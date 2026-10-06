"""0015: widen customer_tickets.status for AI lifecycle states.

Phase 9 added WAITING_FOR_HUMAN (17 chars) and WAITING_FOR_CUSTOMER
(19 chars), which overflow the Phase 5 varchar(16). Live solves crashed
with StringDataRightTruncation the first time HITL paused a ticket.
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_ticket_status_width"
down_revision = "0014_agent_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "customer_tickets",
        "status",
        existing_type=sa.String(16),
        type_=sa.String(32),
        existing_nullable=False,
        schema="biz",
    )


def downgrade() -> None:
    op.alter_column(
        "customer_tickets",
        "status",
        existing_type=sa.String(32),
        type_=sa.String(16),
        existing_nullable=False,
        schema="biz",
    )
