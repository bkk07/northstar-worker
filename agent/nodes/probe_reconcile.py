"""probe_reconcile node (thin): probe-before-retry (Phase 19)."""

from agent.graph.state import WorkerState


def probe_reconcile(state: WorkerState) -> dict:
    """Stub: the row exists unless the test preset a probe outcome."""
    if "probe_status" in state:
        return {}
    return {"probe_status": "exists"}
