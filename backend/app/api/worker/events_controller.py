"""Worker event controller: replayable history plus the live stream."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.core.exceptions import NotFoundError
from app.schemas.worker.events import AuditEventRead
from app.services.worker.event_service import EventService
from app.sse.stream import task_event_stream

router = APIRouter(tags=["worker-events"])

_staff = require_roles("SUPPORT_AGENT")


@router.get("/api/tasks/{task_id}/events/history", response_model=list[AuditEventRead])
def task_event_history(
    task_id: UUID,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> list[AuditEventRead]:
    """Audit events in replay order (the run's chain, oldest first)."""
    return EventService(session).history_for_task(task_id)


@router.get("/api/tasks/{task_id}/events")
def task_event_stream_endpoint(
    task_id: UUID,
    request: Request,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    """Live audit stream (SSE; `Last-Event-ID` resumes from a sequence)."""
    if not EventService(session).task_exists(task_id):
        raise NotFoundError(f"task {task_id} not found")
    try:
        last_event_id = int(request.headers.get("last-event-id", "0"))
    except ValueError:
        last_event_id = 0
    return StreamingResponse(
        task_event_stream(task_id, last_event_id, session, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
