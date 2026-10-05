"""Policy decisions, approvals, clarifications (`worker` schema)."""

import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class PolicyDecision(UUIDPk, Base):
    """One deterministic ALLOW / HUMAN_APPROVAL / BLOCK evaluation."""

    __tablename__ = "policy_decisions"
    __table_args__ = {"schema": "worker"}

    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.tasks.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.task_runs.id"), nullable=True
    )
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.actions.id"), nullable=True
    )
    rule_id: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Approval(UUIDPk, CreatedAt, Base):
    """Single-use, params-hash-bound human approval request."""

    __tablename__ = "approvals"
    __table_args__ = {"schema": "worker"}

    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.tasks.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.task_runs.id"), nullable=True
    )
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.actions.id"), nullable=True
    )
    requested_action: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    params_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    policy_rule_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    approver: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Clarification(UUIDPk, CreatedAt, Base):
    """Operator clarification or customer-information request."""

    __tablename__ = "clarifications"
    __table_args__ = {"schema": "worker"}

    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.tasks.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    answer: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    answered_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
