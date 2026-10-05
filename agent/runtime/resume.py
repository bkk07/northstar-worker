"""Crash resume: restart from the journal, not from wishes (Phase 20).

Rules (§19):
- Last attempt COMPLETED → continue from the last checkpoint.
- Last attempt STARTED and a read → re-run it (drop the partial delta).
- Last attempt STARTED and a **write** → UNKNOWN_OUTCOME: classify, probe.
- Parked approval/clarification → stay parked (the graph ends at once).
"""

from agent.graph.state import initial_state

WRITE_TOOLS = frozenset({"browser_submit"})


def resume_overlay(checkpoint: dict, last_action: dict | None) -> dict:
    """State overlay for a resumed run (pure; the runner loads the rows).

    Returns the checkpoint state adjusted for the interrupted action:
    completed actions resume verbatim; an interrupted write re-enters
    through classify as an unknown outcome; an interrupted read simply
    re-runs (its partial observation is discarded).
    """
    state = dict(checkpoint)
    if not last_action or last_action.get("status") in ("done", "failed", "reconciled"):
        return state
    tool = last_action.get("tool", "")
    action = {k: v for k, v in last_action.items() if k != "result"}
    if tool in WRITE_TOOLS:
        state["last_action"] = {
            **action,
            "result": {
                "ok": False,
                "error": "interrupted mid-commit (crash resume)",
                "error_type": "Interrupted",
                "mutated": False,
                "mutation_key": action.get("mutation_key", ""),
            },
        }
        state["observation_status"] = "failure"
        state["last_observation"] = dict(state["last_action"]["result"])
    else:
        state["last_action"] = action
        state.pop("last_observation", None)
        state.pop("observation_status", None)
    return state


def fresh_or_resumed(
    task_id: str, run_id: str, task_text: str, checkpoint: dict | None, last_action: dict | None
) -> dict:
    """Seed state for a new run, or the resume overlay when one exists."""
    if not checkpoint:
        return dict(initial_state(task_id, run_id, task_text))
    merged = dict(initial_state(task_id, run_id, task_text))
    merged.update(resume_overlay(checkpoint, last_action))
    return merged
