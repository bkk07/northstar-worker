"""classify node (thin): deterministic failure taxonomy (Phase 17)."""

from agent.failures.classifier import classify_failure
from agent.graph.state import WorkerState
from agent.runtime import wiring


def classify(state: WorkerState) -> dict:
    """Type the failure, bump its count, and audit it (pure routing input)."""
    action = state.get("last_action", {})
    result = action.get("result", {})
    if not isinstance(result, dict):
        result = {}
    observation = state.get("last_observation", {})
    failure_type, found = classify_failure(dict(action), result, dict(observation))
    count = state.get("failure", {}).get("count", 0) + 1
    wiring.audit_emitter().emit(
        state["task_id"],
        state.get("run_id", ""),
        "classify",
        "failure.classified",
        status="classified",
        tool=action.get("tool", ""),
        error_type=failure_type,
        retry_count=count - 1,
        payload={"signals": found},
    )
    return {"failure": {"type": failure_type, "count": count}}
