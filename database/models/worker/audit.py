"""Append-only audit journal (`worker.audit_events`).

Every node transition, tool call, policy decision, failure, recovery,
approval, and verification result lands here. UPDATE/DELETE are revoked
for all worker roles (Phase 4 grants); history is never rewritten.
"""

import datetime
import uuid
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, UUIDPk


class AuditEvent(UUIDPk, Base):
    """One immutable audit row with a gapless per-DB sequence number."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_task_seq", "task_id", "seq"), {"schema": "worker"})

    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.tasks.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.task_runs.id"), nullable=True
    )
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True, nullable=False)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
