"""plan node (thin): ordered steps over registered tools (Phase 14)."""

from agent.graph.state import WorkerState


def plan(state: WorkerState) -> dict:
    """Stub: empty plan at cursor zero unless the test preset one."""
    if "plan" in state:
        return {}
    return {"plan": [], "cursor": 0}
