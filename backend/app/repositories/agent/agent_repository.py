"""`biz.agent_runs` + `biz.tool_calls` + `biz.approvals` + `biz.audit_logs`
data access (no business logic)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models.biz.agent import (
    APPROVAL_PENDING,
    RUN_WAITING,
    RUNNING,
    AgentRun,
    Approval,
    AuditLog,
    ToolCall,
)

ACTIVE_RUN_STATUSES = (RUNNING, RUN_WAITING)


class AgentRepository:
    """Thin queries over Phase 9 execution records."""

    def __init__(self, session: Session) -> None:
        self._s = session

    # Runs
    def create_run(self, *, ticket_id) -> AgentRun:
        row = AgentRun(ticket_id=ticket_id, status=RUNNING)
        self._s.add(row)
        self._s.flush()
        return row

    def get_run(self, run_id: uuid.UUID | str) -> AgentRun | None:
        return self._s.get(AgentRun, run_id)

    def active_for_ticket(self, ticket_id: uuid.UUID | str) -> AgentRun | None:
        return self._s.scalars(
            select(AgentRun)
            .where(
                AgentRun.ticket_id == ticket_id,
                AgentRun.status.in_(ACTIVE_RUN_STATUSES),
            )
            .order_by(AgentRun.created_at.desc())
        ).first()

    def latest_for_ticket(self, ticket_id: uuid.UUID | str) -> AgentRun | None:
        return self._s.scalars(
            select(AgentRun)
            .where(AgentRun.ticket_id == ticket_id)
            .order_by(AgentRun.created_at.desc())
        ).first()

    # Tool calls
    def add_tool_call(
        self, *, run_id, tool_name: str, arguments: dict, result: dict | None, status: str
    ) -> ToolCall:
        row = ToolCall(
            agent_run_id=run_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
        )
        self._s.add(row)
        self._s.flush()
        return row

    def list_tool_calls(self, run_id: uuid.UUID | str) -> list[ToolCall]:
        return list(
            self._s.scalars(
                select(ToolCall)
                .where(ToolCall.agent_run_id == run_id)
                .order_by(ToolCall.created_at.asc())
            ).all()
        )

    # Approvals
    def create_approval(
        self, *, ticket_id, run_id, action_type: str, payload: dict
    ) -> Approval:
        row = Approval(
            ticket_id=ticket_id,
            agent_run_id=run_id,
            action_type=action_type,
            action_payload=payload,
            status=APPROVAL_PENDING,
        )
        self._s.add(row)
        self._s.flush()
        return row

    def get_approval(self, approval_id: uuid.UUID | str) -> Approval | None:
        return self._s.get(Approval, approval_id)

    def pending_for_ticket(self, ticket_id: uuid.UUID | str) -> Approval | None:
        return self._s.scalars(
            select(Approval)
            .where(Approval.ticket_id == ticket_id, Approval.status == APPROVAL_PENDING)
            .order_by(Approval.created_at.desc())
        ).first()

    def list_for_ticket(self, ticket_id: uuid.UUID | str) -> list[Approval]:
        """Every approval for one ticket, newest first."""
        return list(
            self._s.scalars(
                select(Approval)
                .where(Approval.ticket_id == ticket_id)
                .order_by(Approval.created_at.desc())
            ).all()
        )

    def list_approvals(
        self, *, status: str | None = None, limit: int = 50
    ) -> list[Approval]:
        stmt = select(Approval).order_by(Approval.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(Approval.status == status)
        return list(self._s.scalars(stmt).all())

    # Audit
    def audit(
        self,
        *,
        ticket_id,
        actor_type: str,
        actor_id,
        event_type: str,
        metadata: dict | None = None,
    ) -> AuditLog:
        from sqlalchemy.exc import IntegrityError

        for _ in range(3):
            seq = (
                self._s.scalar(
                    select(func.coalesce(func.max(AuditLog.sequence), 0)).where(
                        AuditLog.ticket_id == ticket_id
                    )
                )
                or 0
            )
            row = AuditLog(
                ticket_id=ticket_id,
                actor_type=actor_type,
                actor_id=actor_id,
                event_type=event_type,
                meta=metadata or {},
                sequence=seq + 1,
            )
            self._s.add(row)
            try:
                self._s.flush()
                return row
            except IntegrityError:
                self._s.rollback()
                continue
        # Final attempt without swallowing errors.
        row = AuditLog(
            ticket_id=ticket_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            meta=metadata or {},
            sequence=(self._s.scalar(
                select(func.coalesce(func.max(AuditLog.sequence), 0)).where(
                    AuditLog.ticket_id == ticket_id
                )
            ) or 0) + 1,
        )
        self._s.add(row)
        self._s.flush()
        return row

    def list_audits(self, ticket_id: uuid.UUID | str) -> list[AuditLog]:
        return list(
            self._s.scalars(
                select(AuditLog)
                .where(AuditLog.ticket_id == ticket_id)
                .order_by(AuditLog.sequence.asc())
            ).all()
        )
