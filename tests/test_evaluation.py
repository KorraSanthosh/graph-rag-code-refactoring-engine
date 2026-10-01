import pytest
from src.evaluation.complexity_evaluator import ComplexityEvaluator
from src.evaluation.equivalence_checker import SemanticEquivalenceChecker


# ─── Complexity Evaluator Tests ────────────────────────────────────────────────

@pytest.fixture
def evaluator():
    return ComplexityEvaluator()


COMPLEX_CODE = """
def process_data(data):
    result = []
    for item in data:
        if item > 2:
            if item % 2 == 0:
                result.append(item * 2)
            else:
                result.append(item + 10)
        else:
            result.append(item)
    return result
"""

SIMPLE_CODE = """
def process_data(data):
    return [item * 2 if item > 2 and item % 2 == 0
            else item + 10 if item > 2
            else item
            for item in data]
"""


def test_evaluator_returns_report(evaluator):
    report = evaluator.evaluate(COMPLEX_CODE, SIMPLE_CODE, "process_data")
    assert report is not None
    assert report.original_complexity >= 0
    assert report.refactored_complexity >= 0


def test_loc_is_counted(evaluator):
    report = evaluator.evaluate(COMPLEX_CODE, SIMPLE_CODE)
    assert report.original_loc > report.refactored_loc


def test_report_to_dict(evaluator):
    report = evaluator.evaluate(COMPLEX_CODE, SIMPLE_CODE)
    d = report.to_dict()
    assert "original_complexity" in d
    assert "refactored_complexity" in d
    assert "improved" in d


def test_empty_code_does_not_crash(evaluator):
    report = evaluator.evaluate("", "")
    assert report.original_complexity == 0.0
    assert report.refactored_loc == 0


# ─── Semantic Equivalence Checker Tests ───────────────────────────────────────

@pytest.fixture
def checker():
    return SemanticEquivalenceChecker()


ORIGINAL = """
def add(a, b):
    result = 0
    result = a + b
    return result
"""

REFACTORED_CORRECT = """
def add(a, b):
    return a + b
"""

REFACTORED_WRONG = """
def add(a, b):
    return a * b  # Bug: wrong operation
"""


def test_correct_refactoring_passes(checker):
    success, msg = checker.check(ORIGINAL, REFACTORED_CORRECT, "add", [(1, 2), (0, 0), (-1, 5)])
    assert success is True


def test_wrong_refactoring_fails(checker):
    success, msg = checker.check(ORIGINAL, REFACTORED_WRONG, "add", [(1, 2), (3, 4)])
    assert success is False
    assert "differ" in msg.lower() or "expected" in msg.lower()


def test_missing_function_fails(checker):
    success, msg = checker.check(ORIGINAL, "def other(): pass", "add", [(1, 2)])
    assert success is False
    assert "not found" in msg.lower()
