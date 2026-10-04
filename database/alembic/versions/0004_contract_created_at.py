"""0004: creation timestamp on task contracts (newest row is the lock)."""

import sqlalchemy as sa
from alembic import op

revision = "0004_contract_created_at"
down_revision = "0003_fault_calls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_contracts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="worker",
    )


def downgrade() -> None:
    op.drop_column("task_contracts", "created_at", schema="worker")
