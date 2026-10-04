"""plan node (thin): ordered steps over registered tools."""

from agent.contract.models import Contract
from agent.graph.state import WorkerState
from agent.runtime import wiring


def plan(state: WorkerState) -> dict:
    """Plan the locked contract; the stub default only serves topology tests."""
    contract = state.get("contract")
    if not contract:
        return {} if "plan" in state else {"plan": [], "cursor": 0}
    steps = wiring.planning_service().create_plan(Contract.model_validate(contract))
    return {"plan": steps, "cursor": 0}
