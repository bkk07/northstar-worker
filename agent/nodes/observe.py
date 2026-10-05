"""observe node (thin): typed observation + memory write."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def observe(state: WorkerState) -> dict:
    """Normalize the execution result into routing status + observation."""
    action = state.get("last_action", {})
    result = action.get("result", {})
    if not isinstance(result, dict) or "ok" not in result:
        result = {"ok": False, "error": "missing execution result", "error_type": "NO_RESULT"}
    verdict = wiring.observation_service().observe(
        state["task_id"], state["run_id"], dict(action), result
    )
    delta = {
        "last_observation": verdict.observation,
        "observation_status": verdict.status,
        "memory": wiring.memory_store().recent(state["run_id"]),
    }
    if verdict.status == "success":
        plan = state.get("plan", [])
        cursor = state.get("cursor", 0)
        delta["cursor"] = min(cursor + 1, len(plan))
    return delta
