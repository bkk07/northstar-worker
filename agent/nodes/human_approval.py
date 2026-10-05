"""human_approval node (thin): interruptible pause/resume (Phase 22)."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def human_approval(state: WorkerState) -> dict:
    """Park on the first visit; consume the approval into a token on resume."""
    outcome = wiring.approval_service().evaluate(
        state["task_id"],
        state.get("run_id", ""),
        dict(state.get("last_action", {})),
        dict(state.get("policy_decision", {})),
    )
    status = str(outcome.get("approval_status", ""))
    kind = {
        "pending": "approval.park",
        "approved": "approval.resume",
        "rejected": "approval.rejected",
        "expired": "approval.expired",
    }.get(status, "approval.update")
    wiring.audit_emitter().emit(
        state["task_id"],
        state.get("run_id", ""),
        "human_approval",
        kind,
        status=status,
        payload={"approval_id": str(outcome.get("approval_ref", {}).get("id", ""))},
    )
    return outcome
