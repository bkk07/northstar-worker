"""Ops ticket access: queue, detail, status changes."""

from app.repositories.base import BaseRepository
from database.models.biz.ticket import Ticket


class TicketRepository(BaseRepository[Ticket]):
    """Ops-side ticket queries and status writes."""

    def get_by_code(self, code: str) -> Ticket | None:
        """Fetch one ticket by human code."""
        return self._session.query(Ticket).filter(Ticket.code == code).one_or_none()

    def list_paginated(self, page: int, page_size: int) -> tuple[list[Ticket], int]:
        """Ticket queue page (10 per page) plus total count."""
        query = self._session.query(Ticket).order_by(Ticket.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def set_status(self, ticket: Ticket, to_status: str) -> Ticket:
        """Change ticket status, bumping the optimistic-lock version."""
        ticket.status = to_status
        ticket.version = ticket.version + 1
        self._session.flush()
        return ticket

    def create(
        self,
        code: str,
        customer_id,
        order_id,
        subject: str,
        body: str,
        category: str,
    ) -> Ticket:
        """Insert an open ticket (shop raise-ticket form)."""
        ticket = Ticket(
            code=code,
            customer_id=customer_id,
            order_id=order_id,
            subject=subject,
            body=body,
            category=category,
            status="open",
            version=1,
        )
        self._session.add(ticket)
        self._session.flush()
        return ticket
