import pytest
from src.parser.code_parser import CodeParser


@pytest.fixture
def parser():
    return CodeParser()


# ─── Function Extraction Tests ─────────────────────────────────────────────────

def test_extracts_top_level_functions(parser):
    code = "def foo(): pass\ndef bar(): pass"
    result = parser.parse_code(code)
    assert "foo" in result["functions"]
    assert "bar" in result["functions"]


def test_extracts_classes(parser):
    code = "class MyClass:\n    pass"
    result = parser.parse_code(code)
    assert "MyClass" in result["classes"]


def test_scoped_method_names(parser):
    """Methods should be stored as ClassName.method_name, not just method_name."""
    code = "class Engine:\n    def start(self): pass\n    def stop(self): pass"
    result = parser.parse_code(code)
    assert "Engine.start" in result["functions"]
    assert "Engine.stop" in result["functions"]


def test_no_collision_between_class_methods(parser):
    """Two classes with same method name must NOT collide."""
    code = (
        "class A:\n    def process(self): pass\n"
        "class B:\n    def process(self): pass"
    )
    result = parser.parse_code(code)
    assert "A.process" in result["functions"]
    assert "B.process" in result["functions"]
    # Should NOT be just "process"
    assert "process" not in result["functions"]


# ─── Call Edge Tests ───────────────────────────────────────────────────────────

def test_extracts_call_edges(parser):
    code = "def caller():\n    callee()\ndef callee(): pass"
    result = parser.parse_code(code)
    assert ("caller", "callee") in result["calls"]


def test_no_global_scope_edges(parser):
    """Calls made at module level (not inside a function) should be excluded."""
    code = "def foo(): pass\nfoo()"  # call at global scope
    result = parser.parse_code(code)
    # global calls should NOT be included
    assert not any(caller == "global" for caller, _ in result["calls"])


# ─── Import Extraction Tests ───────────────────────────────────────────────────

def test_extracts_imports(parser):
    code = "import os\nfrom pathlib import Path\ndef foo(): pass"
    result = parser.parse_code(code)
    assert any("import os" in imp for imp in result["imports"])
    assert any("from pathlib" in imp for imp in result["imports"])


# ─── Edge Cases ────────────────────────────────────────────────────────────────

def test_empty_file_returns_empty(parser):
    result = parser.parse_code("")
    assert result["functions"] == []
    assert result["classes"] == []
    assert result["calls"] == []


def test_file_with_only_comments(parser):
    result = parser.parse_code("# just a comment\n# another comment")
    assert result["functions"] == []
    assert result["classes"] == []
