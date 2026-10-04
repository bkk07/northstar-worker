"""execute node (thin): journaled MCP tool call (Phase 16 wires the service)."""

from agent.graph.state import WorkerState


def execute(state: WorkerState) -> dict:
    """Stub: records the attempt; the runner journals for real later."""
    attempts = state.get("last_action", {}).get("attempts", 0)
    action = dict(state.get("last_action", {}))
    action["attempts"] = attempts + 1
    return {"last_action": action}
