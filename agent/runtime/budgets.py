"""Run budgets: bounded runs stop safely (Phase 20).

Defaults come from the plan (§19): iterations, tool calls, retries per
action, total retries, recovery attempts, runtime, approval wait. The
runner enforces the measurable ones every transition; the graph edges
fail closed to `finalize` when the state flags a blown budget. Any
breach records BUDGET_EXCEEDED and stops safely.
"""

BUDGET_EXCEEDED = "BUDGET_EXCEEDED"

DEFAULT_LIMITS = {
    "iterations": 40,
    "tool_calls": 60,
    "retries_per_action": 3,
    "total_retries": 10,
    "recovery_attempts": 6,
    "runtime_s": 300,
    "approval_wait_s": 86400,
}


def check(used: dict, limits: dict | None = None) -> str | None:
    """First blown budget name, or None when the run is inside all bounds."""
    bounds = {**DEFAULT_LIMITS, **(limits or {})}
    for name in (
        "iterations",
        "tool_calls",
        "retries_per_action",
        "total_retries",
        "recovery_attempts",
        "runtime_s",
    ):
        if used.get(name, 0) > bounds[name]:
            return name
    return None


def exceeded(state: dict) -> str | None:
    """Budget breach from graph state (edges read this, pure)."""
    if state.get("budget_exceeded"):
        return str(state["budget_exceeded"])
    budgets = state.get("budgets", {})
    return check(budgets.get("used", {}), budgets.get("limits", {}))
