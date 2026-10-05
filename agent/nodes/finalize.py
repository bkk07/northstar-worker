"""finalize node (thin): evidence packet + terminal status (Phase 24).

The terminal mapping lives in `FinalizationService` (pure, pinned by
topology tests); later phases build the evidence packet here.
"""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def finalize(state: WorkerState) -> dict:
    """Fold the decided outcome into a terminal status (deterministic)."""
    return {"status": wiring.finalization_service().status(state)}
