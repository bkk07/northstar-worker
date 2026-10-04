"""finalize node (thin): evidence packet + terminal status (Phase 24).

The stub maps the run's decided outcome to the matching terminal task
state. Later phases build the evidence packet here; the mapping stays.
"""

from agent.graph.state import WorkerState


def finalize(state: WorkerState) -> dict:
    """Fold the decided outcome into a terminal status (deterministic)."""
    if state.get("approval_status") == "rejected":
        return {"status": "blocked"}
    if state.get("policy_decision", {}).get("outcome") == "block":
        return {"status": "blocked"}
    if state.get("contract_status") == "unsupported":
        return {"status": "inconclusive"}
    verdict = state.get("verification", {}).get("verdict", "")
    if verdict == "failed":
        return {"status": "failed"}
    if verdict == "inconclusive":
        return {"status": "inconclusive"}
    if verdict == "verified":
        return {"status": "succeeded"}
    return {"status": "succeeded"}
