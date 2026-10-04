"""Financial history read service."""

import uuid

from sqlalchemy.orm import Session

from app.repositories.commerce.financial_repository import FinancialRepository
from app.schemas.commerce.financial import RefundRead, ReplacementRead
from database.models.biz.financial import Refund, Replacement


class FinancialService:
    """Refund/replacement history reads."""

    def __init__(self, session: Session) -> None:
        self._repos = FinancialRepository(session)

    def list_replacements_by_item(self, order_item_id: uuid.UUID) -> list[ReplacementRead]:
        """Replacements for one order item."""
        return [to_replacement_dto(r) for r in self._repos.list_replacements_by_item(order_item_id)]

    def list_refunds_by_ticket(self, ticket_id: uuid.UUID) -> list[RefundRead]:
        """Refunds linked to one ticket."""
        return [to_refund_dto(r) for r in self._repos.list_refunds_by_ticket(ticket_id)]


def to_replacement_dto(row: Replacement) -> ReplacementRead:
    """Shared replacement mapping (ops services reuse it)."""
    return ReplacementRead(
        id=row.id,
        order_id=row.order_id,
        order_item_id=row.order_item_id,
        customer_id=row.customer_id,
        ticket_id=row.ticket_id,
        status=row.status,
        mutation_key=row.mutation_key,
    )


def to_refund_dto(row: Refund) -> RefundRead:
    """Shared refund mapping (ops services reuse it)."""
    return RefundRead(
        id=row.id,
        order_id=row.order_id,
        customer_id=row.customer_id,
        ticket_id=row.ticket_id,
        amount_paise=row.amount_paise,
        status=row.status,
        mutation_key=row.mutation_key,
    )
