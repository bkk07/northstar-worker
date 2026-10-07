"""Phase 9 agent execution records (`biz.agent_runs`, `biz.tool_calls`,
`biz.approvals`, `biz.audit_logs`; spec §9).

Every AI run on a ticket is persisted: the run itself, each tool call with
arguments + result, any human approval request (PENDING → APPROVED /
REJECTED), and an audit trail of actor events. The support console renders
the AI activity timeline from these rows (SSE pushes live ones).
"""

import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk

RUNNING = "RUNNING"
RUN_WAITING = "WAITING_FOR_HUMAN"
RUN_COMPLETED = "COMPLETED"
RUN_CANCELLED = "CANCELLED"
RUN_FAILED = "FAILED"

APPROVAL_PENDING = "PENDING"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"


class AgentRun(UUIDPk, CreatedAt, Base):
    """One AI attempt at a ticket (spec §9 `agent_runs`).

    `graph_state` holds the full LangGraph checkpoint snapshot so a paused
    run (HITL) resumes the SAME execution after restart/reconnect instead of
    restarting from scratch.
    """

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_ticket_id", "ticket_id"),
        {"schema": "biz"},
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customer_tickets.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RUNNING)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    workflow: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    verification_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )


class ToolCall(UUIDPk, CreatedAt, Base):
    """One tool invocation inside a run (spec §9 `tool_calls`)."""

    __tablename__ = "tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_run_id", "agent_run_id"),
        {"schema": "biz"},
    )

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.agent_runs.id"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DONE")
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Approval(UUIDPk, CreatedAt, Base):
    """Human approval request for a proposed action (spec §9 `approvals`)."""

    __tablename__ = "approvals"
    __table_args__ = (
        Index("ix_approvals_ticket_id", "ticket_id"),
        {"schema": "biz"},
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customer_tickets.id"), nullable=False
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.agent_runs.id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)
    action_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=APPROVAL_PENDING)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    human_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditLog(UUIDPk, CreatedAt, Base):
    """Actor event trail for a ticket (spec §9 `audit_logs`)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_ticket_id", "ticket_id"),
        {"schema": "biz"},
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customer_tickets.id"), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
