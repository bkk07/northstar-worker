"""Idempotency log writes (same transaction as the mutation)."""

import uuid

from app.repositories.base import BaseRepository
from database.models.biz.ops import MutationLog


class MutationRepository(BaseRepository[MutationLog]):
    """Persistence for `biz.mutation_log`."""

    def find_by_key(self, mutation_key: str) -> MutationLog | None:
        """Log row for an idempotency key, if the mutation already ran."""
        return (
            self._session.query(MutationLog)
            .filter(MutationLog.mutation_key == mutation_key)
            .one_or_none()
        )

    def record(self, mutation_key: str, kind: str, entity_id: uuid.UUID) -> MutationLog:
        """Log a committed mutation (caller commits the transaction)."""
        row = MutationLog(mutation_key=mutation_key, kind=kind, entity_id=entity_id)
        self._session.add(row)
        self._session.flush()
        return row
