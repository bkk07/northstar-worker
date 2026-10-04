"""clarification node (thin): operator/customer questions (Phase 22)."""

from agent.graph.state import WorkerState


def clarification(state: WorkerState) -> dict:
    """Stub: stays parked unless the test answered the question."""
    if "clarification_status" in state:
        return {}
    return {"clarification_status": "pending", "clarification_ref": {}}
