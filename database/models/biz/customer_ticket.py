"""Phase 5 customer tickets and conversation (`biz.customer_tickets`,
`biz.customer_ticket_messages`).

Separate from the legacy `biz.tickets` (seed-demo tickets keyed to
`biz.customers`): these rows belong to authenticated `biz.app_users` and
optionally link to a Phase 4 `biz.shop_orders` row. New tickets start OPEN
(spec §11). Bodies are untrusted customer text; the agent treats them as
data, never instructions.
"""

import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk

TICKET_OPEN = "OPEN"
TICKET_AI_PROCESSING = "AI_PROCESSING"
TICKET_WAITING_FOR_CUSTOMER = "WAITING_FOR_CUSTOMER"
TICKET_WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
TICKET_ESCALATED = "ESCALATED"
TICKET_RESOLVED = "RESOLVED"
TICKET_CLOSED = "CLOSED"

CATEGORIES = (
    "REFUND",
    "REPLACEMENT",
    "RETURN",
    "CANCELLATION",
    "DELIVERY",
    "PAYMENT",
    "GENERAL",
)

PRIORITIES = ("LOW", "NORMAL", "HIGH", "URGENT")

SENDER_CUSTOMER = "CUSTOMER"
SENDER_SUPPORT_AGENT = "SUPPORT_AGENT"
SENDER_AI_AGENT = "AI_AGENT"
SENDER_SYSTEM = "SYSTEM"


class CustomerTicket(UUIDPk, CreatedAt, Base):
    """Customer-raised support ticket (spec §9 `tickets`)."""

    __tablename__ = "customer_tickets"
    __table_args__ = (
        Index("ix_customer_tickets_user_id", "user_id"),
        Index("ix_customer_tickets_status", "status"),
        {"schema": "biz"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.app_users.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.shop_orders.id"), nullable=True
    )
    ticket_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TICKET_OPEN)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CustomerTicketMessage(UUIDPk, CreatedAt, Base):
    """One conversation message on a customer ticket (spec §9 `ticket_messages`)."""

    __tablename__ = "customer_ticket_messages"
    __table_args__ = (
        Index("ix_customer_ticket_messages_ticket_id", "ticket_id"),
        {"schema": "biz"},
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customer_tickets.id"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(nullable=False, default=False)
