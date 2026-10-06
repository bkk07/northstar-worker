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
    ) -> CustomerTicketMessage:
        row = CustomerTicketMessage(
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message=message,
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

    def list_messages(self, ticket_id: uuid.UUID | str) -> list[CustomerTicketMessage]:
        return list(
            self._s.scalars(
                select(CustomerTicketMessage)
                .where(CustomerTicketMessage.ticket_id == ticket_id)
                .order_by(CustomerTicketMessage.created_at.asc())
            ).all()
        )

    def count_messages(self, ticket_id: uuid.UUID | str) -> int:
        return (
            self._s.scalar(
                select(func.count())
                .select_from(CustomerTicketMessage)
                .where(CustomerTicketMessage.ticket_id == ticket_id)
            )
            or 0
        )
