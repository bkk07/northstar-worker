"""classify node (thin): deterministic failure taxonomy (Phase 17)."""

from agent.graph.state import WorkerState


def classify(state: WorkerState) -> dict:
    """Stub: network error unless the test preset a failure type."""
    if "failure" in state:
        return {}
    return {"failure": {"type": "network_error", "count": 1}}
