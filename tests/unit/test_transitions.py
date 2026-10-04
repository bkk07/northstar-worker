"""Phase 3: task transitions — legal moves pass, illegal ones raise."""

import pytest

from agent.runtime.transitions import (
    ALLOWED_TRANSITIONS,
    InvalidTransitionError,
    allowed_from,
    assert_allowed,
    assert_not_terminal,
    is_allowed,
)
from northstar_common.enums import TERMINAL_TASK_STATES, TaskState


def test_transition_table_covers_every_state():
    assert set(ALLOWED_TRANSITIONS) == set(TaskState)


def test_happy_path_transitions():
    assert is_allowed(TaskState.PENDING, TaskState.RUNNING)
    assert is_allowed(TaskState.RUNNING, TaskState.WAITING_FOR_APPROVAL)
    assert is_allowed(TaskState.WAITING_FOR_APPROVAL, TaskState.RUNNING)
    assert is_allowed(TaskState.RUNNING, TaskState.SUCCEEDED)
    assert_allowed(TaskState.RUNNING, TaskState.SUCCEEDED)  # no raise


def test_reject_finalizes_blocked():
    assert is_allowed(TaskState.WAITING_FOR_APPROVAL, TaskState.BLOCKED)


def test_terminals_have_no_outgoing():
    for state in TERMINAL_TASK_STATES:
        assert allowed_from(state) == frozenset()
        with pytest.raises(InvalidTransitionError):
            assert_not_terminal(state)


def test_illegal_transitions_raise():
    with pytest.raises(InvalidTransitionError):
        assert_allowed(TaskState.PENDING, TaskState.SUCCEEDED)
    with pytest.raises(InvalidTransitionError):
        assert_allowed(TaskState.SUCCEEDED, TaskState.RUNNING)
    with pytest.raises(InvalidTransitionError):
        assert_allowed(TaskState.WAITING_FOR_APPROVAL, TaskState.SUCCEEDED)
    assert not is_allowed(TaskState.CANCELLED, TaskState.RUNNING)
