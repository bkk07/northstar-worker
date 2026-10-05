"""0007: evaluation runs and results (Phase 27).

`eval_runs` records one suite run (suite name, metrics ledger); each
`eval_results` row scores one scenario (expected vs actual outcome plus
the full score ledger). Reports render from these rows in
`/evaluation`; the JSON/Markdown files under `eval/reports/` stay the
archival copies.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0007_eval_runs"
down_revision = "0006_audit_notify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("suite", sa.String(64), nullable=False),
        sa.Column("scenario_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metrics", JSONB, nullable=False, server_default="{}"),
        sa.Column("report_md", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="worker",
    )
    op.create_table(
        "eval_results",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id", PG_UUID(as_uuid=True), sa.ForeignKey("worker.eval_runs.id"), nullable=False
        ),
        sa.Column("scenario_id", sa.String(16), nullable=False),
        sa.Column("expected_outcome", sa.String(32), nullable=False),
        sa.Column("actual_outcome", sa.String(32), nullable=False),
        sa.Column("outcome_ok", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("scores", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="worker",
    )
    op.create_index("ix_eval_results_run", "eval_results", ["run_id"], schema="worker")


def downgrade() -> None:
    op.drop_index("ix_eval_results_run", table_name="eval_results", schema="worker")
    op.drop_table("eval_results", schema="worker")
    op.drop_table("eval_runs", schema="worker")
