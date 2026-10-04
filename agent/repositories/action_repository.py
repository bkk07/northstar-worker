"""Action repository: validated-action journal rows (`worker.actions`).

`validate` reserves one row per accepted proposal (`proposed`; Phase 16
moves it to STARTED before executing). Nodes never import this package
directly; services and node wiring do (architecture gate).
"""

from uuid import UUID

from sqlalchemy import func, select

from agent.repositories.base import BaseRepository
from database.models.worker.action import Action


class ActionRepository(BaseRepository[Action]):
    """`ns_runner`-role persistence for validated actions."""

    def next_seq(self, run_id: UUID) -> int:
        """Next action sequence for a run (zero-based)."""
        peak = self._session.scalar(select(func.max(Action.seq)).where(Action.run_id == run_id))
        return (peak if peak is not None else -1) + 1

    def reserve(
        self,
        run_id: UUID,
        kind: str,
        tool: str,
        params: dict,
        params_hash: str,
        side_effect: str,
    ) -> Action:
        """Insert a `proposed` action row for a validated proposal."""
        row = Action(
            run_id=run_id,
            seq=self.next_seq(run_id),
            kind=kind,
            tool=tool,
            params=params,
            params_hash=params_hash,
            mutation_key=None,
            side_effect=side_effect,
            status="proposed",
            policy_decision_id=None,
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def list_by_run(self, run_id: UUID) -> list[Action]:
        """All reserved actions for a run, oldest first."""
        return list(
            self._session.scalars(
                select(Action).where(Action.run_id == run_id).order_by(Action.seq)
            ).all()
        )
