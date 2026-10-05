"""0006: NOTIFY the app on every audit insert (Phase 25 live events).

The SSE stream tails `worker.audit_events` through Postgres
LISTEN/NOTIFY: this trigger shouts the task + sequence number on the
`worker_audit_events` channel after every insert. The payload stays
tiny (routing only); subscribers fetch the row by `(task_id, seq)`.
NOTIFY fires at commit, so listeners never see uncommitted rows.
"""

from alembic import op

revision = "0006_audit_notify"
down_revision = "0005_actions_key_lookup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION worker.audit_events_notify()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            PERFORM pg_notify(
                'worker_audit_events',
                NEW.task_id::text || ':' || NEW.seq::text
            );
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_events_notify
        AFTER INSERT ON worker.audit_events
        FOR EACH ROW
        EXECUTE FUNCTION worker.audit_events_notify();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_notify ON worker.audit_events;")
    op.execute("DROP FUNCTION IF EXISTS worker.audit_events_notify();")
