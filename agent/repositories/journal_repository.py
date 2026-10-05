"""Journal repository: action lifecycle rows (`worker.actions`, `worker.action_attempts`).

Journal-first: STARTED rows exist before `execute` calls any tool, and
every attempt is a row (retries append, never edit). `validate` reserves
`proposed` rows via `ActionRepository`; this repository moves them to
STARTED with their idempotency key, or reserves directly when a proposal
row is absent (defensive: execution never runs unlogged).
"""

from uuid import UUID

from sqlalchemy import func, select

from agent.repositories.action_repository import ActionRepository
from agent.repositories.base import BaseRepository
from database.models.worker.action import Action, ActionAttempt


class JournalRepository(BaseRepository[Action]):
    """`ns_runner`-role action/attempt journal (runner + execution service)."""

    def __init__(self, session) -> None:
        super().__init__(session)
        self._actions = ActionRepository(session)

    def find_proposed(self, run_id: UUID, tool: str, params_hash: str) -> Action | None:
        """Newest `proposed` row matching tool + params (None when absent)."""
        rows = self._actions.list_by_run(run_id)
        for row in reversed(rows):
            if (
                row.status == "proposed"
                and row.tool == tool
                and row.params_hash == params_hash
            ):
                return row
        return None

    def start_action(
        self,
        run_id: UUID,
        kind: str,
        tool: str,
        params: dict,
        params_hash: str,
        side_effect: str,
        mutation_key: str,
        policy_decision_id: UUID | None = None,
    ) -> Action:
        """Move the reserved row to STARTED (or reserve+start when absent)."""
        row = self.find_proposed(run_id, tool, params_hash)
        if row is None:
            row = self._actions.reserve(run_id, kind, tool, params, params_hash, side_effect)
        row.status = "started"
        row.mutation_key = mutation_key
        if policy_decision_id is not None:
            row.policy_decision_id = policy_decision_id
        self.flush()
        return self.refresh(row)

    def begin_attempt(self, action_id: UUID, started_at) -> ActionAttempt:
        """Append one attempt row (attempt numbers are gapless per action)."""
        peak = self._session.scalar(
            select(func.max(ActionAttempt.attempt_no)).where(
                ActionAttempt.action_id == action_id
            )
        )
        row = ActionAttempt(
            action_id=action_id,
            attempt_no=(peak if peak is not None else 0) + 1,
            started_at=started_at,
            observation={},
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def end_attempt(
        self,
        attempt: ActionAttempt,
        outcome: str,
        observation: dict,
        error_type: str | None,
        ended_at,
    ) -> ActionAttempt:
        """Close an attempt with its outcome and observation."""
        attempt.outcome = outcome
        attempt.observation = observation
        attempt.error_type = error_type
        attempt.ended_at = ended_at
        self.flush()
        return self.refresh(attempt)

    def finish_action(self, action: Action, status: str) -> Action:
        """Mark an action `done` or `failed` (terminal journal states)."""
        action.status = status
        self.flush()
        return self.refresh(action)

    def list_by_run(self, run_id: UUID) -> list[Action]:
        """All journaled actions for a run, oldest first."""
        return self._actions.list_by_run(run_id)
