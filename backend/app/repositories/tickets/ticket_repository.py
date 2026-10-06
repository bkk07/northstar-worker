"""`biz.customer_tickets` + conversation data access (no business logic)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models.biz.customer_ticket import CustomerTicket, CustomerTicketMessage


class CustomerTicketRepository:
    """Thin queries over Phase 5 customer tickets."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def create_ticket(
        self,
        *,
        user_id: uuid.UUID | str,
        order_id: uuid.UUID | str | None,
        ticket_number: str,
        subject: str,
        description: str,
        category: str,
        priority: str,
    ) -> CustomerTicket:
        row = CustomerTicket(
            user_id=user_id,
            order_id=order_id,
            ticket_number=ticket_number,
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            status="OPEN",
        )
        self._s.add(row)
        self._s.flush()
        return row

    def add_message(
        self,
        *,
        ticket_id,
        sender_type: str,
        sender_id: uuid.UUID | str | None,
        message: str,
        is_internal: bool = False,
    ) -> CustomerTicketMessage:
        row = CustomerTicketMessage(
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message=message,
            is_internal=is_internal,
        )
        self._s.add(row)
        self._s.flush()
        return row

    def get_by_id(self, ticket_id: uuid.UUID | str) -> CustomerTicket | None:
        return self._s.get(CustomerTicket, ticket_id)

    def list_by_user(self, user_id: uuid.UUID | str) -> list[CustomerTicket]:
        return list(
            self._s.scalars(
                select(CustomerTicket)
                .where(CustomerTicket.user_id == user_id)
                .order_by(CustomerTicket.created_at.desc())
            ).all()
        )

    def list_messages(
        self, ticket_id: uuid.UUID | str, *, include_internal: bool = False
    ) -> list[CustomerTicketMessage]:
        stmt = select(CustomerTicketMessage).where(
            CustomerTicketMessage.ticket_id == ticket_id
        )
        if not include_internal:
            stmt = stmt.where(CustomerTicketMessage.is_internal.is_(False))
        return list(
            self._s.scalars(stmt.order_by(CustomerTicketMessage.created_at.asc())).all()
        )

    def count_messages(
        self, ticket_id: uuid.UUID | str, *, include_internal: bool = False
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(CustomerTicketMessage)
            .where(CustomerTicketMessage.ticket_id == ticket_id)
        )
        if not include_internal:
            stmt = stmt.where(CustomerTicketMessage.is_internal.is_(False))
        return self._s.scalar(stmt) or 0

    def count_by_status(self) -> dict[str, int]:
        """Tickets per status for the support dashboard (Phase 6)."""
        rows = self._s.execute(
            select(CustomerTicket.status, func.count()).group_by(CustomerTicket.status)
        ).all()
        return {status: count for status, count in rows}

    def list_all(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
    ) -> list[CustomerTicket]:
        """Every ticket, newest first, with queue filters (Phase 6)."""
        stmt = select(CustomerTicket)
        if status:
            stmt = stmt.where(CustomerTicket.status == status)
        if priority:
            stmt = stmt.where(CustomerTicket.priority == priority)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(
                CustomerTicket.ticket_number.ilike(like)
                | CustomerTicket.subject.ilike(like)
            )
        return list(self._s.scalars(stmt.order_by(CustomerTicket.created_at.desc())).all())
