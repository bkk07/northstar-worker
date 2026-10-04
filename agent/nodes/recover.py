"""recover node (thin): router lookup + counters (Phase 18)."""

from agent.graph.state import WorkerState


def recover(state: WorkerState) -> dict:
    """Stub: re-observe unless the test preset a recovery strategy."""
    if "recovery" in state:
        return {}
    return {"recovery": {"strategy": "re_observe", "counters": {}}}
