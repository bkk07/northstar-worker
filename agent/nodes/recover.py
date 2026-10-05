"""recover node (thin): router lookup + counters (Phase 18)."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def recover(state: WorkerState) -> dict:
    """Route the typed failure, apply the strategy, audit the round."""
    return wiring.recovery_service().recover(state["task_id"], state["run_id"], dict(state))
