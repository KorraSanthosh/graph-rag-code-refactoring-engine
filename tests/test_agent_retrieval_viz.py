
import networkx as nx

from src.agent.refactor_agent import run_agent
from src.evaluation.complexity_evaluator import ComplexityEvaluator
from src.graph.graph_visualizer import GraphVisualizer
from src.retrieval.hybrid_retriever import HybridRetriever

CODE = "def a():\n    return b()\n\n\ndef b():\n    return 1\n"


class FakeLLM:
    def __init__(self):
        self.calls = []

    def get_refactored_code(self, **kw):
        self.calls.append(kw["error_log"])
        return CODE


class FakeVerifier:
    def __init__(self, results):
        self.results = list(results)

    def verify_code(self, code):
        # Equivalence harness runs also come through here; let them pass.
        if "Behavior verified" in code or "equivalence" in code.lower() and "base64" in code:
            return True, "Behavior verified on 1 input(s)."
        return self.results.pop(0)


def test_agent_retries_then_succeeds():
    llm = FakeLLM()
    out = run_agent(CODE, "a", "ctx", 3, llm, FakeVerifier([(False, "boom"), (True, "")]), ComplexityEvaluator())
    assert out["success"] and out["attempts_used"] == 2
    assert llm.calls == [None, "boom"]
    assert out["metrics"]["improved"] is True


def test_agent_stops_at_max_attempts():
    out = run_agent(CODE, "a", "ctx", 2, FakeLLM(), FakeVerifier([(False, "x")] * 2), ComplexityEvaluator())
    assert not out["success"] and out["attempts_used"] == 2
    assert out["refactored_code"] is None and out["error"] == "x"


def test_retriever_without_index_returns_structural_only():
    r = HybridRetriever(client=None)
    assert r.retrieve("code", ["b"]) == "Structural: b."


def test_retriever_semantic_filters_graph_nodes():
    class FakeIndex:
        ntotal = 3

        def search(self, q, k):
            import numpy as np
            return None, np.array([[0, 1, 2]])

    r = HybridRetriever(client=None)
    r.index, r.node_map = FakeIndex(), {0: "a", 1: "b", 2: "c"}
    r._embed = lambda texts: __import__("numpy").zeros((1, 2), dtype="float32")
    assert r.retrieve("code", ["b"]) == "Structural: b. Semantic: a, c."


def test_snippet_extraction():
    snips = HybridRetriever._extract_snippets(["a", "b"], CODE)
    assert snips["a"] == "def a():\n    return b()"
    assert snips["b"].endswith("return 1")


def test_visualizer_html():
    g = nx.DiGraph()
    g.add_node("A", type="class")
    g.add_node("f", type="function")
    g.add_edge("A", "f", relation="CALLS")
    html = GraphVisualizer().to_html(g)
    assert "#e94560" in html and "#0f3460" in html


class _SandboxLike:
    def verify_code(self, code):
        import subprocess
        import sys
        p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=30)
        return p.returncode == 0, p.stdout + p.stderr


def test_sandboxed_equivalence_checks_arguments_and_mutation():
    from src.evaluation.equivalence_checker import SemanticEquivalenceChecker
    chk, sb = SemanticEquivalenceChecker(), _SandboxLike()
    orig = "def add(a, b):\n    return a + b\n"
    assert chk.check_sandboxed(orig, "def add(a, b):\n    r = a + b\n    return r\n", "add", sb)[0]
    ok, msg = chk.check_sandboxed(orig, "def add(a, b):\n    return a - b\n", "add", sb)
    assert not ok and "Behavior changed" in msg
    mut_o = "def f(xs):\n    xs.append(1)\n    return len(xs)\n"
    mut_n = "def f(xs):\n    return len(xs) + 1\n"
    assert not chk.check_sandboxed(mut_o, mut_n, "f", sb)[0]
    assert chk.check_sandboxed(orig, orig, "Cls.method", sb)[0]
