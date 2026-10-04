"""validate node (thin): gate every proposal before policy or tools.

Delegates to the validation service (repository access lives there, not
here). The stub default only serves topology tests.
"""

from agent.contract.models import Contract
from agent.graph.state import WorkerState
from agent.runtime import wiring


def validate(state: WorkerState) -> dict:
    """Check the proposal; reserve the row or route back with the error."""
    contract = state.get("contract")
    action = state.get("last_action", {})
    if not contract:
        if "validation_status" in state:
            return {}
        return {"validation_status": "ok"}
    return wiring.validation_service().check_and_reserve(
        state["run_id"],
        action,
        Contract.model_validate(contract),
        state.get("validation_failures", 0),
    )
