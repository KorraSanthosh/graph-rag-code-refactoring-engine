import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RefactoringReport:
    """Captures before/after quality metrics for a refactoring operation."""
    original_complexity: float
    refactored_complexity: float
    original_loc: int
    refactored_loc: int
    original_maintainability: float
    refactored_maintainability: float
    target_function: str

    @property
    def complexity_delta(self) -> float:
        """Positive = improvement (complexity reduced)."""
        return self.original_complexity - self.refactored_complexity

    @property
    def loc_delta(self) -> int:
        """Negative = fewer lines (usually good)."""
        return self.refactored_loc - self.original_loc

    @property
    def improved(self) -> bool:
        return self.complexity_delta >= 0

    def summary(self) -> str:
        direction = "↓ Better" if self.complexity_delta > 0 else ("= Same" if self.complexity_delta == 0 else "↑ Worse")
        return (
            f"  Cyclomatic Complexity : {self.original_complexity:.1f} → "
            f"{self.refactored_complexity:.1f}  ({direction})\n"
            f"  Lines of Code         : {self.original_loc} → {self.refactored_loc}  "
            f"({'−' if self.loc_delta < 0 else '+'}{abs(self.loc_delta)} lines)\n"
            f"  Maintainability Index : {self.original_maintainability:.1f} → "
            f"{self.refactored_maintainability:.1f}"
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data.update(
            complexity_delta=self.complexity_delta,
            loc_delta=self.loc_delta,
            improved=self.improved,
        )
        return data


class ComplexityEvaluator:
    """
    Evaluates refactoring quality using Radon metrics:
    - Cyclomatic Complexity (CC): branching paths. Lower = simpler.
    - Maintainability Index (MI): 0–100. Higher = more maintainable.
    - Lines of Code (LOC).
    """

    def evaluate(
        self, original_code: str, refactored_code: str, target_function: str = ""
    ) -> RefactoringReport:
        report = RefactoringReport(
            original_complexity=self._avg_complexity(original_code),
            refactored_complexity=self._avg_complexity(refactored_code),
            original_loc=self._count_loc(original_code),
            refactored_loc=self._count_loc(refactored_code),
            original_maintainability=self._maintainability(original_code),
            refactored_maintainability=self._maintainability(refactored_code),
            target_function=target_function,
        )
        logger.info(f"Evaluation complete.\n{report.summary()}")
        return report

    def _avg_complexity(self, code: str) -> float:
        if not code.strip():
            return 0.0
        try:
            from radon.complexity import cc_visit
            results = cc_visit(code)
            if not results:
                return 1.0
            return sum(r.complexity for r in results) / len(results)
        except Exception as e:
            logger.warning(f"Complexity calculation failed: {e}")
            return 0.0

    def _maintainability(self, code: str) -> float:
        try:
            from radon.metrics import mi_visit
            return mi_visit(code, multi=True)
        except Exception as e:
            logger.warning(f"Maintainability calculation failed: {e}")
            return 0.0

    def _count_loc(self, code: str) -> int:
        return sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))
