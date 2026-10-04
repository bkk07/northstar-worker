"""Support tickets and ticket notes (`biz.tickets`, `biz.ticket_notes`).

Ticket bodies are untrusted customer text; the agent treats them as data,
never instructions (plan §23).
"""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class Ticket(UUIDPk, CreatedAt, Base):
    """Support ticket, optionally linked to an order."""

    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_customer_id", "customer_id"),
        {"schema": "biz"},
    )

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customers.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.orders.id"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class TicketNote(UUIDPk, CreatedAt, Base):
    """Internal note or customer reply on a ticket."""

    __tablename__ = "ticket_notes"
    __table_args__ = {"schema": "biz"}

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.tickets.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(120), nullable=False)
    mutation_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
