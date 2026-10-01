import textwrap
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _normalize_source(value: str) -> str:
    """Pasted code is often uniformly indented; dedent it so Python can compile it."""
    code = textwrap.dedent(value.replace("\t", "    ")).strip("\n")
    # A partial copy often leaves only the first line indented; top-level code cannot be.
    lines = code.split("\n")
    if lines and lines[0][:1].isspace():
        lines[0] = lines[0].lstrip()
    return "\n".join(lines) + "\n"


# ─── Request Models ────────────────────────────────────────────────────────────

class RefactorRequest(BaseModel):
    source_code: str = Field(..., max_length=20000, description="Full Python source code to refactor")
    target_function: str = Field(..., description="Name of the function/method to refactor")
    max_attempts: int = Field(3, ge=1, le=5, description="Max retry attempts (1–5)")

    _dedent = field_validator("source_code")(_normalize_source)

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_code": "def process_data():\n    data = [1,2,3,4,5]\n    result = []\n    for item in data:\n        if item > 2:\n            result.append(item * 2 + 10)\n    return result",
                "target_function": "process_data",
                "max_attempts": 3,
            }
        }
    }


class AnalyzeRequest(BaseModel):
    source_code: str = Field(..., max_length=20000, description="Python source code to analyze")

    _dedent = field_validator("source_code")(_normalize_source)


# ─── Response Models ────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    type: str  # "function" | "class"


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class EvaluationMetrics(BaseModel):
    original_complexity: float
    refactored_complexity: float
    complexity_delta: float
    original_loc: int
    refactored_loc: int
    loc_delta: int
    original_maintainability: float
    refactored_maintainability: float
    improved: bool


class RefactorResponse(BaseModel):
    success: bool
    target_function: str
    original_code: str
    refactored_code: Optional[str] = None
    attempts_used: int
    graph_context: str
    graph_data: Optional[GraphData] = None
    metrics: Optional[EvaluationMetrics] = None
    equivalence: Optional[str] = None
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    functions: list[str]
    classes: list[str]
    imports: list[str]
    call_edges: list[tuple[str, str]]
    graph_data: GraphData


class HealthResponse(BaseModel):
    status: str
    docker_available: bool
    model: str
    version: str
    sandbox: str = "unknown"
