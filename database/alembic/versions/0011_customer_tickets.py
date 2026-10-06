"""0011: Phase 5 customer tickets and conversation."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0011_customer_tickets"
down_revision = "0010_shop_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_tickets",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.app_users.id"),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.shop_orders.id"),
            nullable=True,
        ),
        sa.Column("ticket_number", sa.String(16), nullable=False, unique=True),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )
    op.create_index(
        "ix_customer_tickets_user_id", "customer_tickets", ["user_id"], schema="biz"
    )
    op.create_index(
        "ix_customer_tickets_status", "customer_tickets", ["status"], schema="biz"
    )

    op.create_table(
        "customer_ticket_messages",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ticket_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.customer_tickets.id"),
            nullable=False,
        ),
        sa.Column("sender_type", sa.String(16), nullable=False),
        sa.Column("sender_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )
    op.create_index(
        "ix_customer_ticket_messages_ticket_id",
        "customer_ticket_messages",
        ["ticket_id"],
        schema="biz",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_ticket_messages_ticket_id",
        table_name="customer_ticket_messages",
        schema="biz",
    )
    op.drop_table("customer_ticket_messages", schema="biz")
    op.drop_index("ix_customer_tickets_status", table_name="customer_tickets", schema="biz")
    op.drop_index("ix_customer_tickets_user_id", table_name="customer_tickets", schema="biz")
    op.drop_table("customer_tickets", schema="biz")
