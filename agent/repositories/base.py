"""Agent repository base: journal, checkpoint, and read access.

Bound to the `ns_runner` role (writes `worker.*`, reads `biz` through
views). Graph nodes never import this package directly; services do
(architecture gate). Concrete repositories arrive with their phases.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Session-bound persistence helpers for the runner."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ModelT) -> ModelT:
        """Stage an entity (the runtime commits journal transactions)."""
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
