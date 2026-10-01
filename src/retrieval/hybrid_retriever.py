import logging
import re

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines structural graph context (BFS neighbours) with semantic similarity
    search over function bodies (OpenAI embeddings + FAISS).
    """

    def __init__(self, client: OpenAI, model: str = "text-embedding-3-small"):
        self.client = client
        self.model = model
        self.index = None
        self.node_map: dict[int, str] = {}

    def build_index(self, metadata: dict, source_code: str) -> None:
        """Embeds each function snippet and stores it in a FAISS IndexFlatL2."""
        self.index = None
        self.node_map = {}
        try:
            import faiss

            snippets = self._extract_snippets(metadata.get("functions", []), source_code)
            if not snippets:
                return
            names = list(snippets)
            vectors = self._embed([snippets[n] for n in names])
            index = faiss.IndexFlatL2(vectors.shape[1])
            index.add(vectors)
            self.index = index
            self.node_map = dict(enumerate(names))
            logger.info(f"Vector index built with {len(names)} functions.")
        except Exception as e:
            logger.warning(f"Index build failed, using graph context only: {e}")
            self.index = None
            self.node_map = {}

    def retrieve(self, target_code: str, graph_nodes: list[str], top_k: int = 3) -> str:
        """Returns 'Structural: X, Y. Semantic: Z.' context for the target code."""
        structural = f"Structural: {', '.join(graph_nodes) if graph_nodes else 'none'}."
        if len(graph_nodes) >= top_k or self.index is None or self.index.ntotal == 0:
            return structural
        try:
            query = self._embed([target_code])
            k = min(top_k, self.index.ntotal)
            _, ids = self.index.search(query, k)
            semantic = [
                self.node_map[i]
                for i in ids[0]
                if i in self.node_map and self.node_map[i] not in graph_nodes
            ]
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return structural
        if not semantic:
            return structural
        return f"{structural[:-1]}. Semantic: {', '.join(semantic)}."

    def _embed(self, texts: list[str]) -> np.ndarray:
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return np.array([d.embedding for d in resp.data], dtype="float32")

    @staticmethod
    def _extract_snippets(functions: list[str], source_code: str) -> dict[str, str]:
        """Simple line scan: a snippet runs from `def name` to the next line at <= its indent."""
        lines = source_code.splitlines()
        snippets: dict[str, str] = {}
        for name in functions:
            pattern = re.compile(rf"^(\s*)(?:async\s+)?def\s+{re.escape(name)}\b")
            for i, line in enumerate(lines):
                m = pattern.match(line)
                if not m:
                    continue
                indent = len(m.group(1))
                end = i + 1
                while end < len(lines) and (
                    not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > indent
                ):
                    end += 1
                snippets[name] = "\n".join(lines[i:end]).rstrip()
                break
        return snippets
