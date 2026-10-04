"""0002: worker schema, transition enforcement, runner views, grants.

Creates schema `worker` with all §9 worker tables, seeds
`allowed_transitions` from the Phase 3 table (a test asserts the two stay
in sync), enforces task status changes with a trigger, exposes `biz` reads
to the runner through views only, and sets the append-only rule on
`audit_events` (SELECT + INSERT, no UPDATE/DELETE, for every worker role).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_worker"
down_revision = "0001_biz"
branch_labels = None
depends_on = None

# Frozen copy of agent.runtime.transitions.ALLOWED_TRANSITIONS (Phase 3).
# tests/integration/test_schema.py asserts this matches the code table.
ALLOWED_TRANSITIONS = [
    ("pending", "running"),
    ("pending", "cancelled"),
    ("running", "waiting_for_approval"),
    ("running", "waiting_for_clarification"),
    ("running", "waiting_on_customer"),
    ("running", "succeeded"),
    ("running", "failed"),
    ("running", "blocked"),
    ("running", "inconclusive"),
    ("running", "cancelled"),
    ("waiting_for_approval", "running"),
    ("waiting_for_approval", "blocked"),
    ("waiting_for_approval", "cancelled"),
    ("waiting_for_clarification", "running"),
    ("waiting_for_clarification", "cancelled"),
    ("waiting_on_customer", "running"),
    ("waiting_on_customer", "inconclusive"),
    ("waiting_on_customer", "cancelled"),
]


def _ts(name: str, nullable: bool = True) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def _uuid_fk(column: str, target: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        column,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey(target),
        nullable=nullable,
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS worker")

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("text", sa.String(2000), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("current_state", sa.String(40), nullable=False),
        sa.Column("scenario_ref", sa.String(120), nullable=True),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="worker",
    )
    op.create_index("ix_tasks_status", "tasks", ["status"], schema="worker")

    op.create_table(
        "task_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("task_id", "worker.tasks.id"),
        sa.Column("attempt", sa.Integer, nullable=False),
        sa.Column("lease_owner", sa.String(120), nullable=True),
        _ts("lease_expires_at"),
        _ts("heartbeat_at"),
        _ts("started_at"),
        _ts("ended_at"),
        schema="worker",
    )
    op.create_index(
        "uq_task_runs_task_attempt",
        "task_runs",
        ["task_id", "attempt"],
        unique=True,
        schema="worker",
    )

    op.create_table(
        "task_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("run_id", "worker.task_runs.id"),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("node", sa.String(64), nullable=False),
        sa.Column("state", postgresql.JSONB, nullable=False),
        schema="worker",
    )
    op.create_index(
        "uq_task_checkpoints_run_seq",
        "task_checkpoints",
        ["run_id", "seq"],
        unique=True,
        schema="worker",
    )

    op.create_table(
        "task_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("task_id", "worker.tasks.id"),
        sa.Column("contract", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("ambiguity", postgresql.JSONB, nullable=False, server_default="{}"),
        schema="worker",
    )

    op.create_table(
        "policy_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("task_id", "worker.tasks.id"),
        _uuid_fk("run_id", "worker.task_runs.id", nullable=True),
        # action_id FK added after worker.actions exists (circular link).
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_id", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("params", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        schema="worker",
    )

    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("run_id", "worker.task_runs.id"),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("tool", sa.String(64), nullable=False),
        sa.Column("params", postgresql.JSONB, nullable=False),
        sa.Column("params_hash", sa.String(64), nullable=False),
        sa.Column("mutation_key", sa.String(64), unique=True, nullable=True),
        sa.Column("side_effect", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        _uuid_fk("policy_decision_id", "worker.policy_decisions.id", nullable=True),
        schema="worker",
    )
    op.create_index(
        "uq_actions_run_seq", "actions", ["run_id", "seq"], unique=True, schema="worker"
    )
    # Deferred: closes the actions <-> policy_decisions circular link.
    op.create_foreign_key(
        "fk_policy_decisions_action_id_actions",
        "policy_decisions",
        "actions",
        ["action_id"],
        ["id"],
        source_schema="worker",
        referent_schema="worker",
    )

    op.create_table(
        "action_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("action_id", "worker.actions.id"),
        sa.Column("attempt_no", sa.Integer, nullable=False),
        _ts("started_at"),
        _ts("ended_at"),
        sa.Column("outcome", sa.String(32), nullable=True),
        sa.Column("error_type", sa.String(64), nullable=True),
        sa.Column("observation", postgresql.JSONB, nullable=False, server_default="{}"),
        schema="worker",
    )
    op.create_index(
        "uq_action_attempts_action_no",
        "action_attempts",
        ["action_id", "attempt_no"],
        unique=True,
        schema="worker",
    )

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("task_id", "worker.tasks.id"),
        _uuid_fk("run_id", "worker.task_runs.id", nullable=True),
        _uuid_fk("action_id", "worker.actions.id", nullable=True),
        sa.Column("requested_action", sa.String(64), nullable=False),
        sa.Column("params", postgresql.JSONB, nullable=False),
        sa.Column("params_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("policy_rule_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("approver", sa.String(120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        _ts("resolved_at"),
        _ts("expires_at"),
        schema="worker",
    )

    op.create_table(
        "clarifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("task_id", "worker.tasks.id"),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("answer", sa.String(2000), nullable=True),
        sa.Column("answered_by", sa.String(120), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="worker",
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("task_id", "worker.tasks.id"),
        _uuid_fk("run_id", "worker.task_runs.id", nullable=True),
        sa.Column("seq", sa.BigInteger, sa.Identity(), unique=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("node", sa.String(64), nullable=True),
        sa.Column("tool", sa.String(64), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("error_type", sa.String(64), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("policy_result", sa.String(32), nullable=True),
        sa.Column("verification_result", sa.String(32), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        schema="worker",
    )
    op.create_index("ix_audit_events_task_seq", "audit_events", ["task_id", "seq"], schema="worker")

    op.create_table(
        "memory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("run_id", "worker.task_runs.id"),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_ref", sa.String(200), nullable=True),
        sa.Column("trust", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="worker",
    )

    op.create_table(
        "snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("run_id", "worker.task_runs.id"),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False),
        schema="worker",
    )

    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("run_id", "worker.task_runs.id"),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("invariants", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("diff", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        schema="worker",
    )

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("task_id", "worker.tasks.id"),
        sa.Column("packet", postgresql.JSONB, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="worker",
    )

    op.create_table(
        "allowed_transitions",
        sa.Column("from_status", sa.String(40), primary_key=True),
        sa.Column("to_status", sa.String(40), primary_key=True),
        schema="worker",
    )
    transitions_table = sa.table(
        "allowed_transitions",
        sa.column("from_status", sa.String),
        sa.column("to_status", sa.String),
        schema="worker",
    )
    op.bulk_insert(
        transitions_table,
        [{"from_status": frm, "to_status": to} for frm, to in ALLOWED_TRANSITIONS],
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION worker.enforce_task_transition()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                IF NOT EXISTS (
                    SELECT 1 FROM worker.allowed_transitions
                    WHERE from_status = OLD.status AND to_status = NEW.status
                ) THEN
                    RAISE EXCEPTION
                        'illegal task transition: % -> %', OLD.status, NEW.status;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_tasks_transition "
        "BEFORE UPDATE OF status ON worker.tasks "
        "FOR EACH ROW EXECUTE FUNCTION worker.enforce_task_transition()"
    )

    # Runner reads biz through views, never base tables.
    op.execute("CREATE VIEW worker.v_customers AS SELECT id, code, name, email FROM biz.customers")
    op.execute(
        "CREATE VIEW worker.v_orders AS "
        "SELECT id, code, customer_id, status, total_paise, paid_paise, "
        "placed_at, delivered_at FROM biz.orders"
    )
    op.execute(
        "CREATE VIEW worker.v_tickets AS "
        "SELECT id, code, customer_id, order_id, subject, category, status "
        "FROM biz.tickets"
    )

    op.execute("GRANT USAGE ON SCHEMA worker TO ns_app, ns_runner, ns_verifier, ns_test_redteam")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA worker "
        "TO ns_app, ns_runner, ns_test_redteam"
    )
    # Append-only audit: SELECT + INSERT, never UPDATE/DELETE (default-deny
    # already blocks, but this documents the rule explicitly).
    op.execute("REVOKE ALL ON worker.audit_events FROM ns_app, ns_runner, ns_test_redteam")
    op.execute("GRANT SELECT, INSERT ON worker.audit_events TO ns_app, ns_runner, ns_test_redteam")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA worker TO ns_verifier")
    op.execute("GRANT SELECT ON worker.v_customers, worker.v_orders, worker.v_tickets TO ns_runner")
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA worker "
        "TO ns_app, ns_runner, ns_verifier, ns_test_redteam"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA worker "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ns_app, ns_runner, ns_test_redteam"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA worker "
        "GRANT SELECT ON TABLES TO ns_verifier"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_tasks_transition ON worker.tasks")
    op.execute("DROP FUNCTION IF EXISTS worker.enforce_task_transition()")
    op.drop_constraint(
        "fk_policy_decisions_action_id_actions",
        "policy_decisions",
        schema="worker",
        type_="foreignkey",
    )
    for view in ("v_tickets", "v_orders", "v_customers"):
        op.execute(f"DROP VIEW IF EXISTS worker.{view}")
    for table in (
        "allowed_transitions",
        "evidence",
        "verification_results",
        "snapshots",
        "memory_items",
        "audit_events",
        "clarifications",
        "approvals",
        "action_attempts",
        "actions",
        "policy_decisions",
        "task_contracts",
        "task_checkpoints",
        "task_runs",
        "tasks",
    ):
        op.drop_table(table, schema="worker")
