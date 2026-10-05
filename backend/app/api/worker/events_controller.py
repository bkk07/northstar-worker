"""Worker event controller: replayable audit history for a task."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.worker.events import AuditEventRead
from app.services.worker.event_service import EventService

router = APIRouter(tags=["worker-events"])


@router.get("/api/tasks/{task_id}/events/history", response_model=list[AuditEventRead])
def task_event_history(task_id: UUID, session: Session = Depends(get_db)) -> list[AuditEventRead]:
    """Audit events in replay order (the run's chain, oldest first)."""
    return EventService(session).history_for_task(task_id)
