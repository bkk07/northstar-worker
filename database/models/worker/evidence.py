"""Verification snapshots, results, and evidence packets (`worker` schema)."""

import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class Snapshot(UUIDPk, Base):
    """Before/after state snapshot scoped to the contract's entities."""

    __tablename__ = "snapshots"
    __table_args__ = {"schema": "worker"}

    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.task_runs.id"), nullable=False
    )
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)


class VerificationResult(UUIDPk, Base):
    """Independent verifier output for one run."""

    __tablename__ = "verification_results"
    __table_args__ = {"schema": "worker"}

    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.task_runs.id"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    invariants: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    diff: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    computed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Evidence(UUIDPk, CreatedAt, Base):
    """Rendered evidence packet for one task (built from verifier + journal)."""

    __tablename__ = "evidence"
    __table_args__ = {"schema": "worker"}

    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.tasks.id"), nullable=False
    )
    packet: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
