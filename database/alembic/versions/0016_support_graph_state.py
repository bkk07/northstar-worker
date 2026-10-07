"""0016: canonical support-graph persistence (state, workflow, approval TTL)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016_support_graph_state"
down_revision = "0015_ticket_status_width"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("graph_state", JSONB, nullable=True),
        schema="biz",
    )
    op.add_column(
        "agent_runs",
        sa.Column("workflow", sa.String(32), nullable=True),
        schema="biz",
    )
    op.add_column(
        "agent_runs",
        sa.Column("error", sa.Text, nullable=True),
        schema="biz",
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "verification_result", JSONB, nullable=True, server_default="{}"
        ),
        schema="biz",
    )
    op.add_column(
        "approvals",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="biz",
    )


def downgrade() -> None:
    op.drop_column("approvals", "expires_at", schema="biz")
    op.drop_column("agent_runs", "verification_result", schema="biz")
    op.drop_column("agent_runs", "error", schema="biz")
    op.drop_column("agent_runs", "workflow", schema="biz")
    op.drop_column("agent_runs", "graph_state", schema="biz")
