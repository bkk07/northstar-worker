"""0005: journal mutation keys are shareable (idempotent retries reuse keys).

`worker.actions.mutation_key` was UNIQUE, which assumed one row per key.
Deterministic keys (Phase 19) intentionally repeat the key across the
original and its same-key retries — the commit stays idempotent because
`biz.*` keys and `mutation_log` remain UNIQUE. Replace the unique
constraint with a plain lookup index.
"""

from alembic import op

revision = "0005_actions_key_lookup"
down_revision = "0004_contract_created_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_actions_mutation_key", "actions", schema="worker", type_="unique")
    op.create_index("ix_actions_mutation_key", "actions", ["mutation_key"], schema="worker")


def downgrade() -> None:
    op.drop_index("ix_actions_mutation_key", table_name="actions", schema="worker")
    op.create_unique_constraint(
        "uq_actions_mutation_key", "actions", ["mutation_key"], schema="worker"
    )
