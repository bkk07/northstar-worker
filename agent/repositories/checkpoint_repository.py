"""Checkpoint repository: node-transition cache (`worker.task_checkpoints`).

The journal plus checkpoints is authoritative and the LangGraph
checkpointer is a cache (plan §19): one row per node transition, ordered
by `seq` per run. Nodes never import this package directly; the runner
and `graph/checkpointer.py` do (architecture gate).
"""

from uuid import UUID

from sqlalchemy import func, select

from agent.repositories.base import BaseRepository
from database.models.worker.task import TaskCheckpoint


class CheckpointRepository(BaseRepository[TaskCheckpoint]):
    """`ns_runner`-role persistence for graph checkpoints."""

    def next_seq(self, run_id: UUID) -> int:
        """Next sequence number for a run (zero-based, gapless per writer)."""
        peak = self._session.scalar(
            select(func.max(TaskCheckpoint.seq)).where(TaskCheckpoint.run_id == run_id)
        )
        return (peak if peak is not None else -1) + 1

    def save(self, run_id: UUID, node: str, state: dict) -> TaskCheckpoint:
        """Append one checkpoint row (state must be JSON-serializable)."""
        row = TaskCheckpoint(run_id=run_id, seq=self.next_seq(run_id), node=node, state=state)
        self.add(row)
        self.flush()
        return self.refresh(row)

    def latest(self, run_id: UUID) -> TaskCheckpoint | None:
        """Newest checkpoint for a run (resume starts here)."""
        return self._session.scalar(
            select(TaskCheckpoint)
            .where(TaskCheckpoint.run_id == run_id)
            .order_by(TaskCheckpoint.seq.desc())
            .limit(1)
        )

    def history(self, run_id: UUID) -> list[TaskCheckpoint]:
        """All checkpoints for a run, oldest first."""
        return list(
            self._session.scalars(
                select(TaskCheckpoint)
                .where(TaskCheckpoint.run_id == run_id)
                .order_by(TaskCheckpoint.seq)
            ).all()
        )
