import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from src.api.schemas import (
    RefactorRequest,
    RefactorResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    GraphData,
    GraphNode,
    GraphEdge,
    EvaluationMetrics,
)
from src.api.dependencies import AppState, get_app_state
from src.graph.dependency_graph import DependencyGraph
from src.graph.graph_visualizer import GraphVisualizer
from src.agent.refactor_agent import run_agent, stream_agent

router = APIRouter()
_SEMANTIC_THRESHOLD = 3  # matches HybridRetriever.retrieve(top_k=3)
logger = logging.getLogger(__name__)


# ─── Health Check ───────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(state: AppState = Depends(get_app_state)):
    """Returns API health status, Docker availability, and model configuration."""
    return HealthResponse(
        status="ok",
        docker_available=state.verifier._docker_available,
        model=state.model,
        version="1.0.0",
        sandbox=state.verifier.mode,
    )


# ─── Analyze Endpoint ───────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_code(
    request: AnalyzeRequest,
    state: AppState = Depends(get_app_state),
):
    """
    Parses Python source code and returns:
    - Extracted functions, classes, and imports
    - Dependency graph (nodes + edges)

    Use this to discover available target functions before calling /refactor.
    """
    try:
        metadata = state.parser.parse_code(request.source_code)

        dg = DependencyGraph()
        dg.build_from_metadata(metadata)
        graph_dict = dg.to_dict()

        return AnalyzeResponse(
            functions=metadata["functions"],
            classes=metadata["classes"],
            imports=metadata["imports"],
            call_edges=metadata["calls"],
            graph_data=GraphData(
                nodes=[GraphNode(**n) for n in graph_dict["nodes"]],
                edges=[GraphEdge(**e) for e in graph_dict["edges"]],
            ),
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


# ─── Refactor Endpoints ─────────────────────────────────────────────────────────

def _prepare(request: RefactorRequest, state: AppState) -> tuple[str, dict]:
    """Steps 1–3: parse → build graph → retrieve hybrid context. Returns (context, graph_dict)."""
    source_code, target = request.source_code, request.target_function

    try:
        metadata = state.parser.parse_code(source_code)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parse error: {str(e)}")

    dg = DependencyGraph()
    dg.build_from_metadata(metadata)

    if target not in dg.graph:
        available = ", ".join(metadata["functions"][:10])
        raise HTTPException(
            status_code=404,
            detail=f"Function '{target}' not found in graph. Available: [{available}]",
        )

    related = dg.get_related_nodes(target)
    retriever = state.make_retriever()
    if len(related) < _SEMANTIC_THRESHOLD:  # graph context is sparse → worth embedding
        retriever.build_index(metadata, source_code)
    graph_context = retriever.retrieve(_target_snippet(source_code, target), related)
    return graph_context, dg.to_dict()


def _agent_kwargs(request: RefactorRequest, graph_context: str, state: AppState) -> dict:
    return dict(
        source_code=request.source_code,
        target_function=request.target_function,
        graph_context=graph_context,
        max_attempts=request.max_attempts,
        llm=state.llm,
        verifier=state.verifier,
        evaluator=state.evaluator,
    )


def _to_response(result: dict, graph_dict: dict) -> RefactorResponse:
    metrics = EvaluationMetrics(**result["metrics"]) if result["metrics"] else None
    return RefactorResponse(
        success=result["success"],
        target_function=result["target_function"],
        original_code=result["original_code"],
        refactored_code=result["refactored_code"],
        attempts_used=result["attempts_used"],
        graph_context=result["graph_context"],
        graph_data=GraphData(
            nodes=[GraphNode(**n) for n in graph_dict["nodes"]],
            edges=[GraphEdge(**e) for e in graph_dict["edges"]],
        ),
        metrics=metrics,
        equivalence=result.get("equivalence"),
        error=result["error"],
    )


# Sync (`def`) endpoints run in FastAPI's threadpool, so blocking LLM/Docker calls
# never stall the event loop.
@router.post("/refactor", response_model=RefactorResponse, tags=["Refactoring"])
def refactor_code(request: RefactorRequest, state: AppState = Depends(get_app_state)):
    """
    Full Graph-RAG refactoring pipeline:

    1. **Parse** the source code into an AST
    2. **Build** a dependency graph
    3. **Retrieve** structural (BFS) + semantic (FAISS) context for the target
    4. **Refactor** using GPT-4o with the graph-augmented prompt (LangGraph agent)
    5. **Verify** in an isolated sandbox, then differential-test behavior vs. the original
    6. **Evaluate** quality metrics (cyclomatic complexity, LOC, maintainability)
    7. **Retry** with error feedback up to `max_attempts` times
    """
    graph_context, graph_dict = _prepare(request, state)
    try:
        result = run_agent(**_agent_kwargs(request, graph_context, state))
    except Exception as e:
        logger.error(f"Agent failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")
    return _to_response(result, graph_dict)


@router.post("/refactor/stream", tags=["Refactoring"])
def refactor_code_stream(request: RefactorRequest, state: AppState = Depends(get_app_state)):
    """Same pipeline as /refactor, streamed as Server-Sent Events (progress → result)."""
    graph_context, graph_dict = _prepare(request, state)

    def events():
        def sse(payload: dict) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        yield sse({"event": "context", "graph_context": graph_context})
        try:
            for ev in stream_agent(**_agent_kwargs(request, graph_context, state)):
                if ev["event"] == "result":
                    ev["result"] = _to_response(ev["result"], graph_dict).model_dump()
                yield sse(ev)
        except Exception as e:
            logger.error(f"Agent stream failed: {e}", exc_info=True)
            yield sse({"event": "error", "detail": f"LLM error: {str(e)}"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Visualize Endpoint ─────────────────────────────────────────────────────────

@router.post("/visualize", tags=["Analysis"])
def visualize_graph(request: AnalyzeRequest, state: AppState = Depends(get_app_state)):
    """Returns an interactive HTML visualization of the dependency graph."""
    try:
        metadata = state.parser.parse_code(request.source_code)
        dg = DependencyGraph()
        dg.build_from_metadata(metadata)
        html_content = GraphVisualizer().to_html(dg.graph)
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Visualization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Visualization error: {str(e)}")


def _target_snippet(source_code: str, target: str, limit: int = 500) -> str:
    """First `limit` chars of the source starting at the target function's definition."""
    idx = source_code.find(f"def {target}")
    return source_code[idx if idx >= 0 else 0:][:limit]
