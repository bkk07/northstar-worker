"""0003: fault-plan call counter for deterministic nth-call triggers."""

import sqlalchemy as sa
from alembic import op

revision = "0003_fault_calls"
down_revision = "0002_worker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fault_plans",
        sa.Column("calls", sa.Integer, nullable=False, server_default="0"),
        schema="biz",
    )


def downgrade() -> None:
    op.drop_column("fault_plans", "calls", schema="biz")
