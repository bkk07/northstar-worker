"""human_approval node (thin): interruptible pause/resume (Phase 22)."""

from agent.graph.state import WorkerState


def human_approval(state: WorkerState) -> dict:
    """Stub: approved unless the test parked or rejected the request."""
    if "approval_status" in state:
        return {}
    return {"approval_status": "approved", "approval_ref": {}}
