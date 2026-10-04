"""decide node (thin): next typed action from plan, memory, observation."""

from agent.contract.models import Contract
from agent.graph.state import WorkerState
from agent.runtime import wiring


def decide(state: WorkerState) -> dict:
    """Propose one action; the stub default only serves topology tests."""
    contract = state.get("contract")
    if not contract:
        return (
            {}
            if "last_action" in state
            else {"last_action": {"tool": "browser_observe", "params": {}}}
        )
    action = wiring.decision_service().next_action(
        Contract.model_validate(contract),
        state.get("plan", []),
        state.get("cursor", 0),
        state.get("memory", []),
        state.get("last_observation", {}),
        state.get("validation_error", ""),
        state.get("validation_failures", 0),
    )
    return {"last_action": action.model_dump()}
