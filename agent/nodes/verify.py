"""verify node (thin): independent verifier port (Phase 21 wired)."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def verify(state: WorkerState) -> dict:
    """Verify the contract against real DB state; tests may preset a verdict."""
    if "verification" in state:
        return {}
    outcome = wiring.verifier_adapter().verify(state.get("contract", {}), state.get("run_id", ""))
    return {"verification": outcome}
