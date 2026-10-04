"""Refund and replacement reads."""

import uuid

from app.repositories.base import BaseRepository
from database.models.biz.financial import Refund, Replacement


class FinancialRepository(BaseRepository[Refund | Replacement]):
    """Read access to `biz.refunds` and `biz.replacements`."""

    def list_replacements_by_item(self, order_item_id: uuid.UUID) -> list[Replacement]:
        """Replacements for one order item (history for duplicate checks)."""
        return (
            self._session.query(Replacement)
            .filter(Replacement.order_item_id == order_item_id)
            .order_by(Replacement.created_at.desc())
            .all()
        )

    def list_refunds_by_ticket(self, ticket_id: uuid.UUID) -> list[Refund]:
        """Refunds linked to one ticket."""
        return (
            self._session.query(Refund)
            .filter(Refund.ticket_id == ticket_id)
            .order_by(Refund.created_at.desc())
            .all()
        )

    def find_active_replacement(self, order_item_id: uuid.UUID) -> Replacement | None:
        """Active replacement for an item (probe by business identity)."""
        return (
            self._session.query(Replacement)
            .filter(
                Replacement.order_item_id == order_item_id,
                Replacement.status.in_(["pending", "shipped"]),
            )
            .one_or_none()
        )

    def find_active_refund(self, ticket_id: uuid.UUID, order_id: uuid.UUID) -> Refund | None:
        """Active refund for a (ticket, order) identity."""
        return (
            self._session.query(Refund)
            .filter(
                Refund.ticket_id == ticket_id,
                Refund.order_id == order_id,
                Refund.status != "cancelled",
            )
            .one_or_none()
        )
