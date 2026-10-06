"""0008: Phase 2 JWT identity store (`biz.app_users`)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0008_auth_users"
down_revision = "0007_eval_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="CUSTOMER"),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="biz",
    )
    op.create_index("ix_app_users_email", "app_users", ["email"], schema="biz", unique=True)


def downgrade() -> None:
    op.drop_index("ix_app_users_email", table_name="app_users", schema="biz")
    op.drop_table("app_users", schema="biz")
