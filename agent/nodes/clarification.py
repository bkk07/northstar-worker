"""clarification node (thin): operator/customer questions (Phase 22)."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def clarification(state: WorkerState) -> dict:
    """Park on the first visit; carry the answer back on resume."""
    outcome = wiring.clarification_service().evaluate(
        state["task_id"],
        _question(state),
        kind=str(state.get("clarification_kind", "operator")),
    )
    status = str(outcome.get("clarification_status", ""))
    kind = {
        "pending": "clarification.park",
        "answered": "clarification.answered",
        "expired": "clarification.expired",
    }.get(status, "clarification.update")
    wiring.audit_emitter().emit(
        state["task_id"],
        state.get("run_id", ""),
        "clarification",
        kind,
        status=status,
        payload={"clarification_id": str(outcome.get("clarification_ref", {}).get("id", ""))},
    )
    return outcome


def _question(state: WorkerState) -> str:
    """Deterministic question from the contract ambiguity (never LLM text)."""
    contract = state.get("contract", {})
    ambiguity = contract.get("ambiguity", []) if isinstance(contract, dict) else []
    if ambiguity:
        return "Operator input needed: " + "; ".join(str(a) for a in ambiguity)
    return f"Operator input needed for task: {state.get('task_text', '')}"[:1000]
