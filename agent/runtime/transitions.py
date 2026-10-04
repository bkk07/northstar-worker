"""Allowed task-state transitions (single source of truth).

Used by the runner/graph now and by the `worker.allowed_transitions`
table + DB enforcement function in Phase 4. Illegal transitions raise
instead of being representable (plan Phase 3 definition of done).
"""

from northstar_common.enums import TERMINAL_TASK_STATES, TaskState
from northstar_common.errors import NorthstarError


class InvalidTransitionError(NorthstarError):
    """Attempted task-state transition is not allowed."""

    code = "INVALID_TRANSITION"


ALLOWED_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.PENDING: frozenset({TaskState.RUNNING, TaskState.CANCELLED}),
    TaskState.RUNNING: frozenset(
        {
            TaskState.WAITING_FOR_APPROVAL,
            TaskState.WAITING_FOR_CLARIFICATION,
            TaskState.WAITING_ON_CUSTOMER,
            TaskState.SUCCEEDED,
            TaskState.FAILED,
            TaskState.BLOCKED,
            TaskState.INCONCLUSIVE,
            TaskState.CANCELLED,
        }
    ),
    TaskState.WAITING_FOR_APPROVAL: frozenset(
        {TaskState.RUNNING, TaskState.BLOCKED, TaskState.CANCELLED}
    ),
    TaskState.WAITING_FOR_CLARIFICATION: frozenset({TaskState.RUNNING, TaskState.CANCELLED}),
    TaskState.WAITING_ON_CUSTOMER: frozenset(
        {TaskState.RUNNING, TaskState.INCONCLUSIVE, TaskState.CANCELLED}
    ),
    TaskState.SUCCEEDED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.BLOCKED: frozenset(),
    TaskState.INCONCLUSIVE: frozenset(),
    TaskState.CANCELLED: frozenset(),
}


def is_allowed(frm: TaskState, to: TaskState) -> bool:
    """True when a task may move from `frm` to `to`."""
    return to in ALLOWED_TRANSITIONS[frm]


def allowed_from(state: TaskState) -> frozenset[TaskState]:
    """All states directly reachable from `state` (empty for terminal)."""
    return ALLOWED_TRANSITIONS[state]


def assert_allowed(frm: TaskState, to: TaskState) -> None:
    """Validate a transition; raise InvalidTransitionError when illegal."""
    if not is_allowed(frm, to):
        raise InvalidTransitionError(f"illegal task transition: {frm.value} -> {to.value}")


def assert_not_terminal(state: TaskState) -> None:
    """Guard for code paths that only make sense on live tasks."""
    if state in TERMINAL_TASK_STATES:
        raise InvalidTransitionError(f"task is terminal: {state.value}")
