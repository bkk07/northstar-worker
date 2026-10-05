"""Worker tasks, runs, checkpoints, contracts (`worker` schema)."""

import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class Task(UUIDPk, CreatedAt, Base):
    """One operator task; status moves only via `allowed_transitions`."""

    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_status", "status"), {"schema": "worker"})

    text: Mapped[str] = mapped_column(String(2000), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    current_state: Mapped[str] = mapped_column(String(40), nullable=False)
    scenario_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)


class TaskRun(UUIDPk, Base):
    """One lease attempt of a task (crash resume starts a new attempt)."""

    __tablename__ = "task_runs"
    __table_args__ = (
        Index("uq_task_runs_task_attempt", "task_id", "attempt", unique=True),
        {"schema": "worker"},
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.tasks.id"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TaskCheckpoint(UUIDPk, Base):
    """One checkpoint per node transition (resume cache; journal is truth)."""

    __tablename__ = "task_checkpoints"
    __table_args__ = (
        Index("uq_task_checkpoints_run_seq", "run_id", "seq", unique=True),
        {"schema": "worker"},
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.task_runs.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    node: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class TaskContract(UUIDPk, CreatedAt, Base):
    """Validated task contract with ambiguity flags."""

    __tablename__ = "task_contracts"
    __table_args__ = {"schema": "worker"}

    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.tasks.id"), nullable=False
    )
    contract: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ambiguity: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
