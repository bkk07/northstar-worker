"""human_approval node (thin): interruptible pause/resume (Phase 22)."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def human_approval(state: WorkerState) -> dict:
    """Park on the first visit; consume the approval into a token on resume."""
    return wiring.approval_service().evaluate(
        state["task_id"],
        state.get("run_id", ""),
        dict(state.get("last_action", {})),
        dict(state.get("policy_decision", {})),
    )
