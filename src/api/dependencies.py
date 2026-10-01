import logging
import os

from openai import OpenAI
from dotenv import load_dotenv

from src.parser.code_parser import CodeParser
from src.llm.llm_engine import LLMEngine
from src.verifier.sandbox_verifier import SandboxVerifier
from src.evaluation.complexity_evaluator import ComplexityEvaluator
from src.retrieval.hybrid_retriever import HybridRetriever

load_dotenv()
logger = logging.getLogger(__name__)


class AppState:
    """
    Singleton application state — holds all shared service instances.
    Initialized once at startup, injected via FastAPI dependency.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

        model = os.getenv("LLM_MODEL", "gpt-4o")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

        # OPENAI_BASE_URL lets any OpenAI-compatible provider (e.g. Gemini) be used.
        self.openai_client = OpenAI(
            api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None,
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),  # ride out transient 429/503 spikes
        )
        self.parser = CodeParser()
        fallbacks = [m.strip() for m in os.getenv("LLM_FALLBACK_MODELS", "").split(",") if m.strip()]
        self.llm = LLMEngine(
            client=self.openai_client, model=model, temperature=temperature, fallback_models=fallbacks
        )
        self.verifier = SandboxVerifier()
        self.evaluator = ComplexityEvaluator()
        self.model = model

        logger.info(f"AppState initialized. Model: {model}")

    def make_retriever(self) -> HybridRetriever:
        """A fresh retriever per request, so concurrent requests never share an index."""
        return HybridRetriever(
            client=self.openai_client,
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )


# Module-level singleton — initialized once on import
_app_state: AppState | None = None


def get_app_state() -> AppState:
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state
