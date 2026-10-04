"""contract node (thin): task-contract compiler (Phase 13 wires the service)."""

from agent.graph.state import WorkerState


def contract(state: WorkerState) -> dict:
    """Stub: default to a plannable contract unless the test preset one."""
    if "contract_status" in state:
        return {}
    return {"contract": {}, "contract_status": "ok"}
