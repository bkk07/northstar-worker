"""0012: Phase 6 internal notes on ticket messages."""

import sqlalchemy as sa
from alembic import op

revision = "0012_ticket_internal_notes"
down_revision = "0011_customer_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_ticket_messages",
        sa.Column("is_internal", sa.Boolean, nullable=False, server_default="false"),
        schema="biz",
    )


def downgrade() -> None:
    op.drop_column("customer_ticket_messages", "is_internal", schema="biz")
