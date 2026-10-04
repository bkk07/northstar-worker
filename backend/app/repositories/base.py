"""Backend repository base: all SQL lives in repositories.

Services call these methods; controllers never import this package
(architecture gate). One repository class per aggregate in Phase 6+.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Session-bound CRUD helpers for the `ns_app` role."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ModelT) -> ModelT:
        """Stage an entity (caller commits the service transaction)."""
        self._session.add(entity)
        return entity

    def flush(self) -> None:
        """Flush staged writes so constraint violations surface early."""
        self._session.flush()

    def refresh(self, entity: ModelT) -> ModelT:
        """Reload server defaults (ids, timestamps) into the entity."""
        self._session.refresh(entity)
        return entity

    def get_by_id(self, model: type[ModelT], entity_id: UUID) -> ModelT | None:
        """Fetch one row by primary key (None when absent)."""
        return self._session.get(model, entity_id)
