"""Phase 4 checkout orders and mock payments (`biz.shop_orders`,
`biz.shop_order_items`, `biz.shop_payments`).

Separate from the legacy `biz.orders` (seed-demo orders keyed to
`biz.customers`): these rows belong to authenticated `biz.app_users` and are
created at checkout from the Phase 3 cart. Money is integer paise; order
items snapshot product names/prices so later catalog edits never rewrite
history. Statuses: PROCESSING → SHIPPED → DELIVERED (spec §10).
"""

import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk

ORDER_PROCESSING = "PROCESSING"
ORDER_SHIPPED = "SHIPPED"
ORDER_DELIVERED = "DELIVERED"

PAYMENT_SUCCESS = "SUCCESS"
PAYMENT_MOCK_METHOD = "MOCK"


class ShopOrder(UUIDPk, CreatedAt, Base):
    """Customer order created by mock checkout (spec §9 `orders`)."""

    __tablename__ = "shop_orders"
    __table_args__ = (
        Index("ix_shop_orders_user_id", "user_id"),
        {"schema": "biz"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.app_users.id"), nullable=False
    )
    order_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ORDER_PROCESSING)
    subtotal_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    total_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PAYMENT_SUCCESS
    )
    shipping_address: Mapped[str] = mapped_column(String(500), nullable=False)
    ordered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    estimated_delivery: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    delivered_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShopOrderItem(UUIDPk, Base):
    """One order line with product snapshot (spec §9 `order_items`)."""

    __tablename__ = "shop_order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="shop_order_qty_positive"),
        {"schema": "biz"},
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.shop_orders.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.products.id"), nullable=False
    )
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)


class ShopPayment(UUIDPk, CreatedAt, Base):
    """Mock payment for one order (spec §9 `payments`; always succeeds)."""

    __tablename__ = "shop_payments"
    __table_args__ = {"schema": "biz"}

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.shop_orders.id"), unique=True, nullable=False
    )
    payment_reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PAYMENT_SUCCESS)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default=PAYMENT_MOCK_METHOD)
    paid_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
