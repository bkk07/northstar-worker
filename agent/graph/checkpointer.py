"""Graph checkpointer: resume cache over the checkpoint repository.

LangGraph carries live state in memory; this store persists one row per
node transition so a restarted runner resumes from the last checkpoint
(plan §19). Reads/writes go through `CheckpointRepository` (`ns_runner`
role). Tests use the in-memory store; the runner wires Postgres.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CheckpointRecord:
    """One persisted node transition."""

    run_id: str
    seq: int
    node: str
    state: dict


class CheckpointStore(Protocol):
    """Persisted-transition cache (Postgres or in-memory)."""

    def save(self, run_id: str, node: str, state: dict) -> CheckpointRecord:
        """Append a transition; returns the stored record."""
        ...

    def latest(self, run_id: str) -> CheckpointRecord | None:
        """Newest transition for a run (None when the run never ran)."""
        ...


class InMemoryCheckpointStore:
    """Process-local store for graph/test runs without a database."""

    def __init__(self) -> None:
        self._rows: dict[str, list[CheckpointRecord]] = {}

    def save(self, run_id: str, node: str, state: dict) -> CheckpointRecord:
        """Append a transition with the next sequence number."""
        rows = self._rows.setdefault(run_id, [])
        record = CheckpointRecord(run_id=run_id, seq=len(rows), node=node, state=dict(state))
        rows.append(record)
        return record

    def latest(self, run_id: str) -> CheckpointRecord | None:
        """Newest transition for a run (None when absent)."""
        rows = self._rows.get(run_id, [])
        return rows[-1] if rows else None


class PostgresCheckpointStore:
    """`CheckpointStore` over `worker.task_checkpoints` (`ns_runner`)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sessions = session_factory

    def save(self, run_id: str, node: str, state: dict) -> CheckpointRecord:
        """Append a transition in its own short-lived session."""
        from agent.repositories.checkpoint_repository import CheckpointRepository

        session = self._sessions()
        try:
            row = CheckpointRepository(session).save(UUID(run_id), node, state)
            session.commit()
            return CheckpointRecord(
                run_id=run_id, seq=row.seq, node=row.node, state=dict(row.state)
            )
        finally:
            session.close()

    def latest(self, run_id: str) -> CheckpointRecord | None:
        """Newest transition for a run (None when absent)."""
        from agent.repositories.checkpoint_repository import CheckpointRepository

        session = self._sessions()
        try:
            row = CheckpointRepository(session).latest(UUID(run_id))
            if row is None:
                return None
            return CheckpointRecord(
                run_id=run_id, seq=row.seq, node=row.node, state=dict(row.state)
            )
        finally:
            session.close()
