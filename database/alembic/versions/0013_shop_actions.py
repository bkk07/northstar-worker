"""0013: Phase 7 mock business actions."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0013_shop_actions"
down_revision = "0012_ticket_internal_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_actions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ticket_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.customer_tickets.id"),
            nullable=True,
        ),
        sa.Column(
            "order_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.shop_orders.id"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(16), nullable=False),
        sa.Column("amount_paise", sa.Integer, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="DONE"),
        sa.Column("mutation_key", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )
    op.create_index("ix_shop_actions_order_id", "shop_actions", ["order_id"], schema="biz")


def downgrade() -> None:
    op.drop_index("ix_shop_actions_order_id", table_name="shop_actions", schema="biz")
    op.drop_table("shop_actions", schema="biz")
