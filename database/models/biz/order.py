"""Orders and order items (`biz.orders`, `biz.order_items`)."""

import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class Order(UUIDPk, CreatedAt, Base):
    """Customer order; money in integer paise, never paid above total."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("paid_paise <= total_paise", name="paid_lte_total"),
        Index("ix_orders_customer_id", "customer_id"),
        {"schema": "biz"},
    )

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    placed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OrderItem(UUIDPk, Base):
    """One line of an order."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="qty_positive"),
        {"schema": "biz"},
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.orders.id"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
