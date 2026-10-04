"""Refund writes."""

import uuid

from sqlalchemy import func

from app.repositories.base import BaseRepository
from database.models.biz.financial import Refund


class RefundRepository(BaseRepository[Refund]):
    """Persistence for `biz.refunds`."""

    def create(
        self,
        order_id: uuid.UUID,
        customer_id: uuid.UUID,
        ticket_id: uuid.UUID,
        amount_paise: int,
        mutation_key: str,
    ) -> Refund:
        """Stage a pending refund (caller commits with the log row)."""
        row = Refund(
            order_id=order_id,
            customer_id=customer_id,
            ticket_id=ticket_id,
            amount_paise=amount_paise,
            status="pending",
            mutation_key=mutation_key,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def sum_active_for_order(self, order_id: uuid.UUID) -> int:
        """Total non-cancelled refunds on an order (for the paid guard)."""
        total = (
            self._session.query(func.coalesce(func.sum(Refund.amount_paise), 0))
            .filter(Refund.order_id == order_id, Refund.status != "cancelled")
            .scalar()
        )
        return int(total)
