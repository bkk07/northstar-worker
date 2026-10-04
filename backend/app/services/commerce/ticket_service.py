"""Ticket read service."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.commerce.ticket_repository import TicketRepository
from app.schemas.commerce.ticket import TicketRead
from database.models.biz.ticket import Ticket


class TicketService:
    """Ticket queries."""

    def __init__(self, session: Session) -> None:
        self._repos = TicketRepository(session)

    def get_by_id(self, ticket_id: uuid.UUID) -> TicketRead:
        """One ticket or 404."""
        ticket = self._repos.get_by_id(Ticket, ticket_id)
        if ticket is None:
            raise NotFoundError(f"ticket {ticket_id} not found")
        return to_ticket_dto(ticket)


def to_ticket_dto(ticket: Ticket) -> TicketRead:
    """Shared ticket mapping (ops services reuse it)."""
    return TicketRead(
        id=ticket.id,
        code=ticket.code,
        customer_id=ticket.customer_id,
        order_id=ticket.order_id,
        subject=ticket.subject,
        body=ticket.body,
        category=ticket.category,
        status=ticket.status,
        version=ticket.version,
    )
