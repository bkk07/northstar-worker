"""0014: Phase 9 agent runs, tool calls, approvals, audit logs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0014_agent_runs"
down_revision = "0013_shop_actions"
branch_labels = None
depends_on = None


def _created_updated() -> list:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ticket_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.customer_tickets.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="RUNNING"),
        sa.Column("intent", sa.String(32), nullable=True),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_created_updated(),
        schema="biz",
    )
    op.create_index("ix_agent_runs_ticket_id", "agent_runs", ["ticket_id"], schema="biz")

    op.create_table(
        "tool_calls",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_run_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.agent_runs.id"),
            nullable=False,
        ),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("arguments", JSONB, nullable=False, server_default="{}"),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="DONE"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_created_updated(),
        schema="biz",
    )
    op.create_index("ix_tool_calls_run_id", "tool_calls", ["agent_run_id"], schema="biz")

    op.create_table(
        "approvals",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ticket_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.customer_tickets.id"),
            nullable=False,
        ),
        sa.Column(
            "agent_run_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.agent_runs.id"),
            nullable=True,
        ),
        sa.Column("action_type", sa.String(16), nullable=False),
        sa.Column("action_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("human_note", sa.Text, nullable=True),
        *_created_updated(),
        schema="biz",
    )
    op.create_index("ix_approvals_ticket_id", "approvals", ["ticket_id"], schema="biz")

    op.create_table(
        "audit_logs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ticket_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("biz.customer_tickets.id"),
            nullable=False,
        ),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("sequence", sa.Integer, nullable=False, server_default="0"),
        *_created_updated(),
        schema="biz",
    )
    op.create_index("ix_audit_logs_ticket_id", "audit_logs", ["ticket_id"], schema="biz")


def downgrade() -> None:
    op.drop_index("ix_audit_logs_ticket_id", table_name="audit_logs", schema="biz")
    op.drop_table("audit_logs", schema="biz")
    op.drop_index("ix_approvals_ticket_id", table_name="approvals", schema="biz")
    op.drop_table("approvals", schema="biz")
    op.drop_index("ix_tool_calls_run_id", table_name="tool_calls", schema="biz")
    op.drop_table("tool_calls", schema="biz")
    op.drop_index("ix_agent_runs_ticket_id", table_name="agent_runs", schema="biz")
    op.drop_table("agent_runs", schema="biz")
