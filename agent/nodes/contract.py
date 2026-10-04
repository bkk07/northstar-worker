"""contract node (thin): compile and lock the task contract."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def contract(state: WorkerState) -> dict:
    """Resolve entities, compile, persist; the edge reads the status."""
    result = wiring.contract_service().build_contract(state["task_id"], state["task_text"])
    return {"contract": result.model_dump(), "contract_status": result.status}
