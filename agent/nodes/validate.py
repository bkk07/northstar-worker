"""validate node (thin): schema/capability/binding checks (Phase 14)."""

from agent.graph.state import WorkerState


def validate(state: WorkerState) -> dict:
    """Stub: actions pass unless the test preset a verdict."""
    if "validation_status" in state:
        return {}
    return {"validation_status": "ok"}
