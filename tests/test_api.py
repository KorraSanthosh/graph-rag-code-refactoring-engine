import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import dependencies
from src.api.routes import router
from src.api.security import GuardMiddleware
from src.evaluation.complexity_evaluator import ComplexityEvaluator
from src.parser.code_parser import CodeParser
from src.retrieval.hybrid_retriever import HybridRetriever
from src.verifier.sandbox_verifier import SandboxVerifier

ORIGINAL = """
def helper(x):
    return x * 2 + 10


def process_data():
    data = [1, 2, 3, 4, 5]
    result = []
    for item in data:
        if item > 2:
            result.append(helper(item))
    return result
"""
GOOD = """
def helper(x):
    return x * 2 + 10


def process_data():
    return [helper(i) for i in [1, 2, 3, 4, 5] if i > 2]
"""
BROKEN = "def process_data(:\n    pass"
WRONG = """
def helper(x):
    return x * 2 + 10


def process_data():
    return []
"""


class ScriptedLLM:
    def __init__(self, outputs):
        self.outputs, self.errors = list(outputs), []

    def get_refactored_code(self, **kw):
        self.errors.append(kw["error_log"])
        return self.outputs.pop(0)


class FakeState:
    model = "fake"

    def __init__(self, llm):
        self.parser = CodeParser()
        self.llm = llm
        self.verifier = SandboxVerifier(fallback="subprocess")
        self.verifier._docker_available = False
        self.evaluator = ComplexityEvaluator()

    def make_retriever(self):
        return HybridRetriever(client=None)


def make_client(llm, **guard):
    app = FastAPI()
    app.add_middleware(GuardMiddleware, **guard)
    app.include_router(router, prefix="/api/v1")
    state = FakeState(llm)
    app.dependency_overrides[dependencies.get_app_state] = lambda: state
    return TestClient(app), state


def post(client, path="/api/v1/refactor", **body):
    payload = {"source_code": ORIGINAL, "target_function": "process_data", **body}
    return client.post(path, json=payload)


def test_health():
    client, _ = make_client(ScriptedLLM([]))
    data = client.get("/api/v1/health").json()
    assert data["status"] == "ok" and data["sandbox"] == "subprocess"


def test_analyze_and_visualize():
    client, _ = make_client(ScriptedLLM([]))
    r = client.post("/api/v1/analyze", json={"source_code": ORIGINAL})
    assert r.status_code == 200
    assert set(r.json()["functions"]) == {"helper", "process_data"}
    v = client.post("/api/v1/visualize", json={"source_code": ORIGINAL})
    assert v.status_code == 200 and "text/html" in v.headers["content-type"]


def test_refactor_success_with_equivalence_and_metrics():
    client, _ = make_client(ScriptedLLM([GOOD]))
    r = post(client)
    body = r.json()
    assert r.status_code == 200 and body["success"]
    assert body["refactored_code"] == GOOD.strip() or body["refactored_code"] == GOOD
    assert "Behavior verified" in body["equivalence"]
    assert body["metrics"]["improved"] is True
    assert body["graph_data"]["nodes"]


def test_refactor_retries_after_crash_and_after_behavior_change():
    llm = ScriptedLLM([BROKEN, WRONG, GOOD])
    client, _ = make_client(llm)
    body = post(client, max_attempts=3).json()
    assert body["success"] and body["attempts_used"] == 3
    assert "SyntaxError" in llm.errors[1]
    assert "Behavior changed" in llm.errors[2]


def test_refactor_fails_after_max_attempts():
    client, _ = make_client(ScriptedLLM([WRONG, WRONG]))
    body = post(client, max_attempts=2).json()
    assert not body["success"] and body["attempts_used"] == 2
    assert body["refactored_code"] is None and body["error"]


def test_unknown_function_404_and_bad_input_422():
    client, _ = make_client(ScriptedLLM([]))
    assert post(client, target_function="nope").status_code == 404
    assert client.post("/api/v1/refactor", json={"source_code": "x" * 30000, "target_function": "f"}).status_code == 422


def test_llm_failure_returns_502():
    class Boom:
        def get_refactored_code(self, **kw):
            raise RuntimeError("quota")

    client, _ = make_client(Boom())
    assert post(client).status_code == 502


def test_stream_emits_progress_then_result():
    client, _ = make_client(ScriptedLLM([GOOD]))
    r = post(client, path="/api/v1/refactor/stream")
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    kinds = [e["event"] for e in events]
    assert kinds[0] == "context" and kinds[-1] == "result"
    assert [e["node"] for e in events if e["event"] == "progress"] == ["refactor_node", "verify_node", "evaluate_node"]
    assert events[-1]["result"]["success"]


def test_access_key_required_when_configured():
    client, _ = make_client(ScriptedLLM([GOOD]), access_key="secret", rate_limit=0)
    assert post(client).status_code == 401
    ok = client.post(
        "/api/v1/refactor",
        json={"source_code": ORIGINAL, "target_function": "process_data"},
        headers={"X-Access-Key": "secret"},
    )
    assert ok.status_code == 200


def test_rate_limit():
    client, _ = make_client(ScriptedLLM([GOOD, GOOD]), rate_limit=1)
    assert post(client).status_code == 200
    assert post(client).status_code == 429


@pytest.mark.parametrize("code,ok", [("print('hi')", True), ("raise ValueError('x')", False)])
def test_subprocess_verifier(code, ok):
    v = SandboxVerifier(fallback="subprocess")
    v._docker_available = False
    assert v.verify_code(code)[0] is ok


def test_subprocess_verifier_timeout_and_disabled():
    v = SandboxVerifier(timeout=1, fallback="subprocess")
    v._docker_available = False
    ok, log = v.verify_code("while True: pass")
    assert not ok and "timed out" in log
    d = SandboxVerifier(fallback="disabled")
    d._docker_available = False
    assert d.mode == "disabled" and not d.verify_code("print(1)")[0]
