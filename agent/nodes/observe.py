"""observe node (thin): typed observation + memory write (Phase 16)."""

from agent.graph.state import WorkerState


def observe(state: WorkerState) -> dict:
    """Stub: success unless the test preset an observation outcome."""
    if "observation_status" in state:
        return {"last_observation": state.get("last_observation", {})}
    return {"last_observation": {}, "observation_status": "success"}
