"""Idempotency helpers shared by every ops mutation service.

Same key twice returns the same entity; the `mutation_log` row is written
in the same transaction as the mutation itself.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError
from app.repositories.ops.mutation_repository import MutationRepository
from database.models.biz.ops import MutationLog


class MutationService:
    """Lookup-or-record for `Idempotency-Key` handling."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repos = MutationRepository(session)

    def find(self, mutation_key: str) -> MutationLog | None:
        """Prior log row for a key (replay path), if any."""
        return self._repos.find_by_key(mutation_key)

    def require_kind(self, row: MutationLog, kind: str) -> None:
        """Reject a key reused for a different mutation kind."""
        if row.kind != kind:
            raise ConflictError(f"idempotency key already used for {row.kind}")

    def record(self, mutation_key: str, kind: str, entity_id) -> None:
        """Log a mutation (flush; the owning service commits)."""
        self._repos.record(mutation_key, kind, entity_id)

    @staticmethod
    def missing_row(kind: str) -> AppError:
        """Log row without an entity: server-side inconsistency (500)."""
        return AppError(f"mutation log points to a missing {kind} row")
