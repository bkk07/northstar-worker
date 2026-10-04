"""Mutation-log reads (probe-before-retry support)."""

from app.repositories.base import BaseRepository
from database.models.biz.ops import MutationLog


class ProbeRepository(BaseRepository[MutationLog]):
    """Idempotency-log reads (probe-before-retry support)."""

    def find_by_key(self, mutation_key: str) -> MutationLog | None:
        """Mutation-log row for an idempotency key, if any."""
        return (
            self._session.query(MutationLog)
            .filter(MutationLog.mutation_key == mutation_key)
            .one_or_none()
        )
