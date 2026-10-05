"""Worker event service: replayable audit history for a task.

History is seq-ordered so the Control Center timeline — and any
reconstruction — replays the run exactly as it happened. History is
never rewritten (UPDATE/DELETE revoked for all worker roles).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.worker.events import AuditEventRead
from database.models.worker.audit import AuditEvent
from database.models.worker.task import Task


class EventService:
    """Read-only audit history over `worker.audit_events` (`ns_app`)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def history_for_task(self, task_id: UUID) -> list[AuditEventRead]:
        """Every event for the task, oldest first (404 when absent)."""
        if self._session.get(Task, task_id) is None:
            raise NotFoundError(f"task {task_id} not found")
        rows = (
            self._session.query(AuditEvent)
            .filter(AuditEvent.task_id == task_id)
            .order_by(AuditEvent.seq.asc())
            .all()
        )
        return [self._to_dto(row) for row in rows]

    @staticmethod
    def _to_dto(row: AuditEvent) -> AuditEventRead:
        return AuditEventRead(
            id=row.id,
            task_id=row.task_id,
            run_id=row.run_id,
            seq=row.seq,
            ts=row.ts,
            node=row.node,
            tool=row.tool,
            kind=row.kind,
            status=row.status,
            error_type=row.error_type,
            retry_count=row.retry_count,
            duration_ms=row.duration_ms,
            policy_result=row.policy_result,
            verification_result=row.verification_result,
            payload=dict(row.payload or {}),
        )
