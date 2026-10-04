"""0001: business schema, roles, trigram index, refund guard.

Creates schema `biz`, all §9 business tables, the four DB roles, the
look-alike trigram index, and the last-defense trigger that rejects
refunds exceeding the order's paid amount.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_biz"
down_revision = None
branch_labels = None
depends_on = None

ROLE_PASSWORD = "northstar"  # local-dev parity only, never production

ROLES = ("ns_app", "ns_runner", "ns_verifier", "ns_test_redteam")

CREATE_ROLES = (
    "DO $$ BEGIN\n"
    + "\n".join(
        f"  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{r}') THEN\n"
        f"    CREATE ROLE {r} WITH LOGIN PASSWORD '{ROLE_PASSWORD}';\n"
        "  END IF;"
        for r in ROLES
    )
    + "\nEND $$;"
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS biz")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(CREATE_ROLES)

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(16), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="biz",
    )
    # Look-alike search ("Priya Nair" vs "Priya Nayar"): trigram GIN index.
    op.execute(
        "CREATE INDEX ix_customers_name_trgm ON biz.customers USING gin (lower(name) gin_trgm_ops)"
    )

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(16), unique=True, nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_paise", sa.Integer, nullable=False),
        sa.Column("paid_paise", sa.Integer, nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("paid_paise <= total_paise", name="paid_lte_total"),
        sa.ForeignKeyConstraint(["customer_id"], ["biz.customers.id"]),
        schema="biz",
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"], schema="biz")

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("unit_paise", sa.Integer, nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.CheckConstraint("qty > 0", name="qty_positive"),
        sa.ForeignKeyConstraint(["order_id"], ["biz.orders.id"]),
        schema="biz",
    )

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(16), unique=True, nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["biz.customers.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["biz.orders.id"]),
        schema="biz",
    )
    op.create_index("ix_tickets_status", "tickets", ["status"], schema="biz")
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"], schema="biz")

    op.create_table(
        "ticket_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("mutation_key", sa.String(64), unique=True, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["biz.tickets.id"]),
        schema="biz",
    )

    op.create_table(
        "refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_paise", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mutation_key", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("amount_paise > 0", name="amount_positive"),
        sa.ForeignKeyConstraint(["order_id"], ["biz.orders.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["biz.customers.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["biz.tickets.id"]),
        schema="biz",
    )
    op.create_index(
        "uq_refunds_ticket_order_active",
        "refunds",
        ["ticket_id", "order_id"],
        unique=True,
        schema="biz",
        postgresql_where=sa.text("status <> 'cancelled'"),
    )
    # Last defense: total non-cancelled refunds on an order never exceed paid.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION biz.check_refund_within_paid()
        RETURNS trigger AS $$
        DECLARE
            paid_amount integer;
            refunded_total integer;
        BEGIN
            SELECT paid_paise INTO paid_amount
            FROM biz.orders WHERE id = NEW.order_id;
            SELECT COALESCE(SUM(amount_paise), 0) INTO refunded_total
            FROM biz.refunds
            WHERE order_id = NEW.order_id
              AND status <> 'cancelled'
              AND id IS DISTINCT FROM NEW.id;
            IF refunded_total + NEW.amount_paise > paid_amount THEN
                RAISE EXCEPTION
                    'refund exceeds paid amount: order %, paid %, would refund %',
                    NEW.order_id, paid_amount, refunded_total + NEW.amount_paise;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_refunds_within_paid "
        "BEFORE INSERT OR UPDATE OF amount_paise, status, order_id ON biz.refunds "
        "FOR EACH ROW EXECUTE FUNCTION biz.check_refund_within_paid()"
    )

    op.create_table(
        "replacements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mutation_key", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["biz.orders.id"]),
        sa.ForeignKeyConstraint(["order_item_id"], ["biz.order_items.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["biz.customers.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["biz.tickets.id"]),
        schema="biz",
    )
    op.create_index(
        "uq_replacements_item_active",
        "replacements",
        ["order_item_id"],
        unique=True,
        schema="biz",
        postgresql_where=sa.text("status IN ('pending', 'shipped')"),
    )

    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_key", sa.String(32), unique=True, nullable=False),
        sa.Column("params", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        schema="biz",
    )

    op.create_table(
        "mutation_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mutation_key", sa.String(64), unique=True, nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="biz",
    )

    op.create_table(
        "ops_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_name", sa.String(120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        schema="biz",
    )

    op.create_table(
        "fault_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fault_type", sa.String(64), nullable=False),
        sa.Column("target", sa.String(200), nullable=False),
        sa.Column("trigger", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("params", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("armed", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        schema="biz",
    )

    op.execute("GRANT USAGE ON SCHEMA biz TO ns_app, ns_runner, ns_verifier, ns_test_redteam")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA biz "
        "TO ns_app, ns_test_redteam"
    )
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA biz TO ns_verifier")
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA biz TO ns_app, ns_verifier, ns_test_redteam"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA biz "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ns_app, ns_test_redteam"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA biz "
        "GRANT SELECT ON TABLES TO ns_verifier"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_refunds_within_paid ON biz.refunds")
    op.execute("DROP FUNCTION IF EXISTS biz.check_refund_within_paid()")
    for table in (
        "fault_plans",
        "ops_sessions",
        "mutation_log",
        "policies",
        "replacements",
        "refunds",
        "ticket_notes",
        "tickets",
        "order_items",
        "orders",
        "customers",
    ):
        op.drop_table(table, schema="biz")
    # Roles own no objects, but schema grants and default privileges block
    # DROP ROLE: revoke everything first, then drop the empty schemas.
    for schema in ("biz", "worker"):
        op.execute(
            f"REVOKE ALL ON SCHEMA {schema} FROM ns_app, ns_runner, ns_verifier, ns_test_redteam"
        )
        op.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE postgres "
            f"IN SCHEMA {schema} REVOKE ALL ON TABLES "
            "FROM ns_app, ns_runner, ns_verifier, ns_test_redteam"
        )
    op.execute("DROP SCHEMA IF EXISTS worker")
    op.execute("DROP SCHEMA IF EXISTS biz")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    for role in ROLES:
        op.execute(f"DROP ROLE IF EXISTS {role}")
