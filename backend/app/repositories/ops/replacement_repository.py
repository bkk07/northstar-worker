"""Replacement writes."""

import uuid

from app.repositories.base import BaseRepository
from database.models.biz.financial import Replacement


class ReplacementRepository(BaseRepository[Replacement]):
    """Persistence for `biz.replacements`."""

    def create(
        self,
        order_id: uuid.UUID,
        order_item_id: uuid.UUID,
        customer_id: uuid.UUID,
        ticket_id: uuid.UUID,
        mutation_key: str,
    ) -> Replacement:
        """Stage a pending replacement (caller commits with the log row)."""
        row = Replacement(
            order_id=order_id,
            order_item_id=order_item_id,
            customer_id=customer_id,
            ticket_id=ticket_id,
            status="pending",
            mutation_key=mutation_key,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def find_active_by_item(self, order_item_id: uuid.UUID) -> Replacement | None:
        """Active (pending/shipped) replacement for an item, if any."""
        return (
            self._session.query(Replacement)
            .filter(
                Replacement.order_item_id == order_item_id,
                Replacement.status.in_(["pending", "shipped"]),
            )
            .one_or_none()
        )
