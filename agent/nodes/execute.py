"""execute node (thin): journaled MCP tool call."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def execute(state: WorkerState) -> dict:
    """Run the validated action; stash the journaled outcome for `observe`."""
    action = dict(state.get("last_action", {}))
    attempts = action.get("attempts", 0)
    result = wiring.execution_service().execute(state["task_id"], state["run_id"], action)
    wiring.audit_emitter().emit(
        state["task_id"],
        state.get("run_id", ""),
        "execute",
        "tool.call",
        tool=action.get("tool", ""),
        payload={
            "action_id": str(result.action_id),
            "mutation_key": str(result.mutation_key or ""),
        },
    )
    return {
        "last_action": {
            **action,
            "attempts": attempts + 1,
            "action_id": result.action_id,
            "mutation_key": result.mutation_key,
            "result": result.to_result_dict(),
        }
    }
