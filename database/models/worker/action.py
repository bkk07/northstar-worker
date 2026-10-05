"""Journaled actions and attempts (`worker.actions`, `worker.action_attempts`).

Journal-first: STARTED rows exist before `execute`; nothing runs unlogged.
"""

import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, UUIDPk


class Action(UUIDPk, Base):
    """One validated action with its idempotency key and policy link."""

    __tablename__ = "actions"
    __table_args__ = (
        Index("uq_actions_run_seq", "run_id", "seq", unique=True),
        {"schema": "worker"},
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.task_runs.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    params_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mutation_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    side_effect: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("worker.policy_decisions.id"),
        nullable=True,
    )


class ActionAttempt(UUIDPk, Base):
    """One execution attempt of an action (retries are rows, not edits)."""

    __tablename__ = "action_attempts"
    __table_args__ = (
        Index("uq_action_attempts_action_no", "action_id", "attempt_no", unique=True),
        {"schema": "worker"},
    )

    action_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.actions.id"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
