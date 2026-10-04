"""Ops plumbing: idempotency log, sessions, fault plans (`biz` schema)."""

import datetime
import uuid

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class MutationLog(UUIDPk, CreatedAt, Base):
    """One row per committed ops mutation, written atomically with it."""

    __tablename__ = "mutation_log"
    __table_args__ = {"schema": "biz"}

    mutation_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)


class OpsSession(UUIDPk, Base):
    """Browser session behind the `/ops` cookie (fault target)."""

    __tablename__ = "ops_sessions"
    __table_args__ = {"schema": "biz"}

    agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(nullable=False, default=False)


class FaultPlan(UUIDPk, Base):
    """Armed chaos fault, consumed once (control plane only)."""

    __tablename__ = "fault_plans"
    __table_args__ = {"schema": "biz"}

    fault_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(200), nullable=False)
    trigger: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    armed: Mapped[bool] = mapped_column(nullable=False, default=True)
    consumed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
