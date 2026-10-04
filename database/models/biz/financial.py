"""Refunds and replacements (`biz.refunds`, `biz.replacements`).

Duplicate prevention (plan §18): UNIQUE mutation keys plus partial unique
indexes on the active business identity, so a retried mutation collides
instead of duplicating.
"""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class Refund(UUIDPk, CreatedAt, Base):
    """Refund against a paid order; total refunds never exceed paid."""

    __tablename__ = "refunds"
    __table_args__ = (
        Index(
            "uq_refunds_ticket_order_active",
            "ticket_id",
            "order_id",
            unique=True,
            postgresql_where="status <> 'cancelled'",
        ),
        {"schema": "biz"},
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.orders.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customers.id"), nullable=False
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.tickets.id"), nullable=False
    )
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    mutation_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class Replacement(UUIDPk, CreatedAt, Base):
    """Replacement for one order item; at most one active per item."""

    __tablename__ = "replacements"
    __table_args__ = (
        Index(
            "uq_replacements_item_active",
            "order_item_id",
            unique=True,
            postgresql_where="status IN ('pending', 'shipped')",
        ),
        {"schema": "biz"},
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.orders.id"), nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.order_items.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customers.id"), nullable=False
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.tickets.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    mutation_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
