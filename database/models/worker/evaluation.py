"""Evaluation runs and per-scenario scores (`worker` schema)."""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class EvalRun(UUIDPk, CreatedAt, Base):
    """One suite run: metrics ledger plus the rendered report."""

    __tablename__ = "eval_runs"
    __table_args__ = {"schema": "worker"}

    suite: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    report_md: Mapped[str] = mapped_column(Text, nullable=False, default="")


class EvalResult(UUIDPk, CreatedAt, Base):
    """One scored scenario inside a run."""

    __tablename__ = "eval_results"
    __table_args__ = {"schema": "worker"}

    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("worker.eval_runs.id"), nullable=False
    )
    scenario_id: Mapped[str] = mapped_column(String(16), nullable=False)
    expected_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    actual_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
