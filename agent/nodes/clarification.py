"""clarification node (thin): operator/customer questions (Phase 22)."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def clarification(state: WorkerState) -> dict:
    """Park on the first visit; carry the answer back on resume."""
    return wiring.clarification_service().evaluate(
        state["task_id"],
        _question(state),
        kind=str(state.get("clarification_kind", "operator")),
    )


def _question(state: WorkerState) -> str:
    """Deterministic question from the contract ambiguity (never LLM text)."""
    contract = state.get("contract", {})
    ambiguity = contract.get("ambiguity", []) if isinstance(contract, dict) else []
    if ambiguity:
        return "Operator input needed: " + "; ".join(str(a) for a in ambiguity)
    return f"Operator input needed for task: {state.get('task_text', '')}"[:1000]
