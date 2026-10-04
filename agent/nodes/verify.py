"""verify node (thin): independent verifier port (Phase 21 wires it)."""

from agent.graph.state import WorkerState


def verify(state: WorkerState) -> dict:
    """Stub: VERIFIED unless the test preset a verification verdict."""
    if "verification" in state:
        return {}
    return {"verification": {"verdict": "verified", "invariants": [], "diff": {}}}
