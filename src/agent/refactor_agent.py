import logging
from typing import Any, Iterator, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from src.evaluation.equivalence_checker import SemanticEquivalenceChecker

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State carried through the refactor → verify → evaluate loop."""
    source_code: str
    target_function: str
    graph_context: str
    refactored_code: Optional[str]
    error_log: Optional[str]
    attempts: int
    max_attempts: int
    success: bool
    evaluation_report: Optional[dict]
    equivalence: Optional[str]


def build_agent(llm: Any, verifier: Any, evaluator: Any, checker: Any = None):
    """Compiles the LangGraph state machine using the given services."""
    checker = checker or SemanticEquivalenceChecker()

    def refactor_node(state: AgentState) -> dict:
        attempt = state["attempts"] + 1
        logger.info(f"Refactoring attempt {attempt}/{state['max_attempts']}")
        code = llm.get_refactored_code(
            original_code=state["source_code"],
            graph_context=state["graph_context"],
            target_function=state["target_function"],
            error_log=state["error_log"],
            complexity_before=evaluator._avg_complexity(state["source_code"]),
        )
        return {"refactored_code": code, "attempts": attempt}

    def verify_node(state: AgentState) -> dict:
        code = state["refactored_code"] or ""
        verified, logs = verifier.verify_code(code)
        if not verified:
            logger.warning(f"Attempt {state['attempts']} failed verification: {logs[:200]}")
            return {"success": False, "error_log": logs, "equivalence": None}

        same, note = checker.check_sandboxed(
            state["source_code"], code, state["target_function"], verifier
        )
        if not same:
            logger.warning(f"Attempt {state['attempts']} changed behavior: {note[:200]}")
            return {"success": False, "error_log": note, "equivalence": None}

        logger.info(f"Verification passed on attempt {state['attempts']}.")
        return {"success": True, "error_log": None, "equivalence": note}

    def evaluate_node(state: AgentState) -> dict:
        try:
            report = evaluator.evaluate(
                state["source_code"], state["refactored_code"] or "", state["target_function"]
            )
            return {"evaluation_report": report.to_dict()}
        except Exception as e:
            logger.warning(f"Evaluation failed (non-critical): {e}")
            return {"evaluation_report": None}

    def should_retry(state: AgentState) -> Literal["evaluate_node", "refactor_node", "__end__"]:
        if state["success"]:
            return "evaluate_node"
        if state["attempts"] < state["max_attempts"]:
            return "refactor_node"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("refactor_node", refactor_node)
    graph.add_node("verify_node", verify_node)
    graph.add_node("evaluate_node", evaluate_node)
    graph.set_entry_point("refactor_node")
    graph.add_edge("refactor_node", "verify_node")
    graph.add_conditional_edges(
        "verify_node",
        should_retry,
        {"evaluate_node": "evaluate_node", "refactor_node": "refactor_node", END: END},
    )
    graph.add_edge("evaluate_node", END)
    return graph.compile()


def _initial_state(source_code: str, target_function: str, graph_context: str, max_attempts: int) -> AgentState:
    return {
        "source_code": source_code,
        "target_function": target_function,
        "graph_context": graph_context,
        "refactored_code": None,
        "error_log": None,
        "attempts": 0,
        "max_attempts": max_attempts,
        "success": False,
        "evaluation_report": None,
        "equivalence": None,
    }


def _config(max_attempts: int) -> dict:
    # Each attempt takes 2 steps (refactor + verify), plus evaluate.
    return {"recursion_limit": 2 * max_attempts + 5}


def _result(final: AgentState) -> dict:
    success = final["success"]
    return {
        "success": success,
        "target_function": final["target_function"],
        "original_code": final["source_code"],
        "refactored_code": final["refactored_code"] if success else None,
        "attempts_used": final["attempts"],
        "graph_context": final["graph_context"],
        "metrics": final["evaluation_report"],
        "equivalence": final["equivalence"],
        "error": None if success else final["error_log"],
    }


def run_agent(
    source_code: str,
    target_function: str,
    graph_context: str,
    max_attempts: int,
    llm: Any,
    verifier: Any,
    evaluator: Any,
    checker: Any = None,
) -> dict:
    """
    Runs the agentic loop and returns a dict whose keys match RefactorResponse
    (graph_data is added by the caller). LLM errors propagate to the caller.
    """
    agent = build_agent(llm, verifier, evaluator, checker)
    final = agent.invoke(
        _initial_state(source_code, target_function, graph_context, max_attempts),
        _config(max_attempts),
    )
    return _result(final)


def stream_agent(
    source_code: str,
    target_function: str,
    graph_context: str,
    max_attempts: int,
    llm: Any,
    verifier: Any,
    evaluator: Any,
    checker: Any = None,
) -> Iterator[dict]:
    """
    Same as run_agent but yields progress events as nodes complete:
    {"event": "progress", "node": ..., "attempt": n, "max_attempts": m, "success": bool}
    and finally {"event": "result", "result": {...}}.
    """
    agent = build_agent(llm, verifier, evaluator, checker)
    state = _initial_state(source_code, target_function, graph_context, max_attempts)
    for update in agent.stream(state, _config(max_attempts), stream_mode="updates"):
        for node, changes in update.items():
            state = {**state, **(changes or {})}
            yield {
                "event": "progress",
                "node": node,
                "attempt": state["attempts"],
                "max_attempts": max_attempts,
                "success": state["success"],
            }
    yield {"event": "result", "result": _result(state)}
