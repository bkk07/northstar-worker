"""Phase 3 storefront catalog and cart (`biz.products`, `biz.product_policies`,
`biz.carts`, `biz.cart_items`).

Money is integer paise (repo convention). Cart item prices are snapshots:
later product edits never rewrite an active cart.
"""

import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk

CART_OPEN = "OPEN"
CART_ORDERED = "ORDERED"


class Product(UUIDPk, CreatedAt, Base):
    """Sellable product (spec §9 `products`)."""

    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_category", "category"),
        {"schema": "biz"},
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProductPolicy(UUIDPk, CreatedAt, Base):
    """Per-product return/refund/replacement/cancellation policy (spec §9)."""

    __tablename__ = "product_policies"
    __table_args__ = {"schema": "biz"}

    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.products.id"), unique=True, nullable=False
    )
    return_allowed: Mapped[bool] = mapped_column(nullable=False, default=True)
    return_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    refund_allowed: Mapped[bool] = mapped_column(nullable=False, default=True)
    replacement_allowed: Mapped[bool] = mapped_column(nullable=False, default=True)
    replacement_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    cancellation_allowed: Mapped[bool] = mapped_column(nullable=False, default=True)
    warranty_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Cart(UUIDPk, CreatedAt, Base):
    """One open cart per user (spec §9 `carts`)."""

    __tablename__ = "carts"
    __table_args__ = (
        Index("ix_carts_user_id", "user_id"),
        {"schema": "biz"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.app_users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CART_OPEN)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CartItem(UUIDPk, Base):
    """One cart line with a price snapshot (spec §9 `cart_items`)."""

    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="cart_qty_positive"),
        {"schema": "biz"},
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.carts.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
