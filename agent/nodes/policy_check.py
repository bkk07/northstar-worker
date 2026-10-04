"""policy_check node (thin): deterministic eligibility + authorization."""

from agent.contract.models import Contract
from agent.graph.state import WorkerState
from agent.policy.facts import gather_facts
from agent.runtime import wiring


def policy_check(state: WorkerState) -> dict:
    """Evaluate, persist, and attach the commit token when owed."""
    contract = Contract.model_validate(state["contract"])
    action = dict(state.get("last_action", {}))
    gateway = wiring.mcp_gateway()
    facts = gather_facts(state["task_id"], contract, action, gateway)
    result = wiring.policy_service().check_and_persist(
        state["task_id"], state["run_id"], action, contract, facts
    )
    delta = {
        "policy_decision": {
            "outcome": result.outcome,
            "rule_id": result.rule_id,
            "reason": result.reason,
        }
    }
    if result.token:
        delta["last_action"] = {
            **action,
            "params": {**action.get("params", {}), "token": result.token},
        }
    return delta
