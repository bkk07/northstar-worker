"""0009: Phase 3 storefront catalog and cart."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0009_shop_catalog"
down_revision = "0008_auth_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("brand", sa.String(120), nullable=False, server_default=""),
        sa.Column("price_paise", sa.Integer, nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("stock", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )
    op.create_index("ix_products_category", "products", ["category"], schema="biz")

    op.create_table(
        "product_policies",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.products.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("return_allowed", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("return_window_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("refund_allowed", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("replacement_allowed", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("replacement_window_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("cancellation_allowed", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("warranty_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("policy_text", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )

    op.create_table(
        "carts",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.app_users.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )
    op.create_index("ix_carts_user_id", "carts", ["user_id"], schema="biz")

    op.create_table(
        "cart_items",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cart_id", PG_UUID(as_uuid=True), sa.ForeignKey("biz.carts.id"), nullable=False
        ),
        sa.Column(
            "product_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.products.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price_paise", sa.Integer, nullable=False),
        sa.CheckConstraint("quantity > 0", name="cart_qty_positive"),
        schema="biz",
    )


def downgrade() -> None:
    op.drop_table("cart_items", schema="biz")
    op.drop_index("ix_carts_user_id", table_name="carts", schema="biz")
    op.drop_table("carts", schema="biz")
    op.drop_table("product_policies", schema="biz")
    op.drop_index("ix_products_category", table_name="products", schema="biz")
    op.drop_table("products", schema="biz")
