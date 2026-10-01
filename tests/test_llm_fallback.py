import httpx
import pytest
from openai import InternalServerError, BadRequestError

from src.llm.llm_engine import LLMEngine


def _err(cls, status):
    req = httpx.Request("POST", "http://x")
    return cls("boom", response=httpx.Response(status, request=req), body=None)


class _Client:
    def __init__(self, behaviors):
        self.behaviors, self.models = behaviors, []
        self.chat = type("C", (), {"completions": self})()

    def create(self, model, **kw):
        self.models.append(model)
        b = self.behaviors[model]
        if isinstance(b, Exception):
            raise b
        msg = type("M", (), {"content": f"```python\n{b}\n```"})()
        return type("R", (), {"choices": [type("Ch", (), {"message": msg})()]})()


def _run(client, fallbacks):
    return LLMEngine(client, model="a", fallback_models=fallbacks).get_refactored_code("x=1", "ctx", "f")


def test_falls_back_on_overload():
    c = _Client({"a": _err(InternalServerError, 503), "b": "y = 2"})
    assert _run(c, ["b"]) == "y = 2" and c.models == ["a", "b"]


def test_does_not_fall_back_on_client_error():
    c = _Client({"a": _err(BadRequestError, 400), "b": "y = 2"})
    with pytest.raises(BadRequestError):
        _run(c, ["b"])
    assert c.models == ["a"]


def test_raises_when_all_models_fail():
    c = _Client({"a": _err(InternalServerError, 503), "b": _err(InternalServerError, 503)})
    with pytest.raises(InternalServerError):
        _run(c, ["b"])
