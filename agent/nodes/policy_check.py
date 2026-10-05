"""policy_check node (thin): deterministic eligibility + authorization."""

from agent.contract.models import Contract
from agent.graph.state import WorkerState
from agent.policy.facts import gather_facts
from agent.runtime import wiring


def policy_check(state: WorkerState) -> dict:
    """Evaluate, persist, and attach the commit token when owed.

    The terminal gate runs first: a minor submit ahead of a doomed major
    BLOCKs with the major's rule (persisted against the synthetic major
    action) so the run ends before its first commit.
    """
    contract = Contract.model_validate(state["contract"])
    action = dict(state.get("last_action", {}))
    gateway = wiring.mcp_gateway()
    service = wiring.policy_service()
    terminal = service.pending_terminal_block(
        state["task_id"], state["run_id"], action, contract, gateway
    )
    if terminal is not None:
        major, result = terminal
        service.persist(state["task_id"], state["run_id"], major, result)
        delta = {
            "policy_decision": {
                "outcome": result.outcome,
                "rule_id": result.rule_id,
                "reason": result.reason,
            }
        }
        wiring.audit_emitter().emit(
            state["task_id"],
            state.get("run_id", ""),
            "policy_check",
            "policy.decision",
            tool=action.get("tool", ""),
            policy_result=result.outcome,
            payload={
                "rule_id": result.rule_id,
                "reason": result.reason,
                "terminal_gate": True,
                "held_effect": (action.get("params", {}) or {}).get("effect", ""),
                "decided_effect": (major.get("params", {}) or {}).get("effect", ""),
            },
        )
        return delta
    facts = gather_facts(state["task_id"], contract, action, gateway)
    result = service.check_and_persist(state["task_id"], state["run_id"], action, contract, facts)
    delta = {
        "policy_decision": {
            "outcome": result.outcome,
            "rule_id": result.rule_id,
            "reason": result.reason,
        }
    }
    wiring.audit_emitter().emit(
        state["task_id"],
        state.get("run_id", ""),
        "policy_check",
        "policy.decision",
        tool=action.get("tool", ""),
        policy_result=result.outcome,
        payload={"rule_id": result.rule_id, "reason": result.reason},
    )
    if result.token:
        delta["last_action"] = {
            **action,
            "params": {**action.get("params", {}), "token": result.token},
        }
    return delta
