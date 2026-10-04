"""policy_check node (thin): deterministic policy engine (Phase 15)."""

from agent.graph.state import WorkerState


def policy_check(state: WorkerState) -> dict:
    """Stub: ALLOW unless the test preset a decision."""
    if "policy_decision" in state:
        return {}
    return {
        "policy_decision": {
            "outcome": "allow",
            "rule_id": "P-NOTE-001",
            "reason": "stub: Phase 15 decides for real",
        }
    }
