from src.api.schemas import AnalyzeRequest, RefactorRequest


def test_indented_paste_is_dedented():
    code = "    def f(x):\n        return x\n"
    assert RefactorRequest(source_code=code, target_function="f").source_code == "def f(x):\n    return x\n"
    assert AnalyzeRequest(source_code=code).source_code.startswith("def f")


def test_clean_code_unchanged():
    code = "def f():\n    return 1\n"
    assert AnalyzeRequest(source_code=code).source_code == code


def test_only_first_line_indented():
    code = "  def f(x):\n    return x\n\ndef g():\n    return 1\n"
    out = AnalyzeRequest(source_code=code).source_code
    compile(out, "<t>", "exec")
    assert out.startswith("def f")
