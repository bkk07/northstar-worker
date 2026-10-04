"""decide node (thin): next typed action (Phase 14 wires the service)."""

from agent.graph.state import WorkerState


def decide(state: WorkerState) -> dict:
    """Stub: a harmless read action unless the test preset one."""
    if "last_action" in state:
        return {}
    return {"last_action": {"tool": "browser_observe", "params": {}}}
