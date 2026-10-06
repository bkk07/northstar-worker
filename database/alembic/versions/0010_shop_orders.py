"""0010: Phase 4 checkout orders and mock payments."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0010_shop_orders"
down_revision = "0009_shop_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_orders",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.app_users.id"),
            nullable=False,
        ),
        sa.Column("order_number", sa.String(16), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="PROCESSING"),
        sa.Column("subtotal_paise", sa.Integer, nullable=False),
        sa.Column("total_paise", sa.Integer, nullable=False),
        sa.Column("payment_status", sa.String(16), nullable=False, server_default="SUCCESS"),
        sa.Column("shipping_address", sa.String(500), nullable=False),
        sa.Column(
            "ordered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("estimated_delivery", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )
    op.create_index("ix_shop_orders_user_id", "shop_orders", ["user_id"], schema="biz")

    op.create_table(
        "shop_order_items",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.shop_orders.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.products.id"),
            nullable=False,
        ),
        sa.Column("product_name_snapshot", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price_paise", sa.Integer, nullable=False),
        sa.CheckConstraint("quantity > 0", name="shop_order_qty_positive"),
        schema="biz",
    )

    op.create_table(
        "shop_payments",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.shop_orders.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("payment_reference", sa.String(32), nullable=False, unique=True),
        sa.Column("amount_paise", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="SUCCESS"),
        sa.Column("method", sa.String(16), nullable=False, server_default="MOCK"),
        sa.Column(
            "paid_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )


def downgrade() -> None:
    op.drop_table("shop_payments", schema="biz")
    op.drop_table("shop_order_items", schema="biz")
    op.drop_index("ix_shop_orders_user_id", table_name="shop_orders", schema="biz")
    op.drop_table("shop_orders", schema="biz")
