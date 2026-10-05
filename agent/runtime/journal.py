"""Journal writer: journal-first facade over short-lived sessions.

Every public method opens a session, commits, and closes it, so nodes
and services never hold sessions open across tool calls. Returned
handles are plain data (ids and keys), never ORM objects — ORM rows
must not cross session boundaries.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from agent.ports.clock import ClockPort
from agent.repositories.journal_repository import JournalRepository


@dataclass(frozen=True)
class StartedAction:
    """A journaled action ready to execute (STARTED, key assigned)."""

    action_id: UUID
    seq: int
    mutation_key: str


@dataclass(frozen=True)
class AttemptHandle:
    """An open attempt row (closed by `end_attempt`)."""

    attempt_id: UUID
    attempt_no: int


class JournalWriter:
    """Transactional journal access for the execution service and runner."""

    def __init__(self, session_factory: Callable[[], Session], clock: ClockPort) -> None:
        self._sessions = session_factory
        self._clock = clock

    def new_mutation_key(self) -> str:
        """Fresh idempotency key (one per STARTED action)."""
        return uuid.uuid4().hex

    def start_action(
        self,
        run_id: str,
        kind: str,
        tool: str,
        params: dict,
        params_hash: str,
        side_effect: str,
        policy_decision_id: str | None = None,
    ) -> StartedAction:
        """Journal STARTED before the tool runs (journal-first)."""
        session = self._sessions()
        try:
            row = JournalRepository(session).start_action(
                UUID(run_id),
                kind,
                tool,
                params,
                params_hash,
                side_effect,
                self.new_mutation_key(),
                UUID(policy_decision_id) if policy_decision_id else None,
            )
            session.commit()
            return StartedAction(
                action_id=row.id, seq=row.seq, mutation_key=row.mutation_key or ""
            )
        finally:
            session.close()

    def begin_attempt(self, action_id: UUID) -> AttemptHandle:
        """Open one attempt row for a STARTED action."""
        session = self._sessions()
        try:
            row = JournalRepository(session).begin_attempt(action_id, self._clock.now())
            session.commit()
            return AttemptHandle(attempt_id=row.id, attempt_no=row.attempt_no)
        finally:
            session.close()

    def end_attempt(
        self,
        attempt_id: UUID,
        outcome: str,
        observation: dict,
        error_type: str | None = None,
    ) -> None:
        """Close an attempt with its outcome and observation."""
        from database.models.worker.action import ActionAttempt

        session = self._sessions()
        try:
            attempt = session.get(ActionAttempt, attempt_id)
            if attempt is None:
                raise KeyError(f"unknown attempt: {attempt_id}")
            JournalRepository(session).end_attempt(
                attempt, outcome, observation, error_type, self._clock.now()
            )
            session.commit()
        finally:
            session.close()

    def finish_action(self, action_id: UUID, status: str) -> None:
        """Mark an action `done` or `failed`."""
        from database.models.worker.action import Action

        session = self._sessions()
        try:
            action = session.get(Action, action_id)
            if action is None:
                raise KeyError(f"unknown action: {action_id}")
            JournalRepository(session).finish_action(action, status)
            session.commit()
        finally:
            session.close()
