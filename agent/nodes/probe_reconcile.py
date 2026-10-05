"""probe_reconcile node (thin): probe-before-retry (Phase 19)."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def probe_reconcile(state: WorkerState) -> dict:
    """Probe the failed commit, then adopt, park, or arm a same-key retry."""
    return wiring.reconciliation_service().probe_and_decide(
        state["task_id"], state["run_id"], dict(state)
    )
