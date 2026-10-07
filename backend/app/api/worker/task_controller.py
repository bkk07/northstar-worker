"""Worker task controller: minimal create / read for the task queue."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.schemas.worker.tasks import TaskCreate, TaskRead
from app.services.worker.task_service import TaskService

router = APIRouter(tags=["worker-tasks"])

_staff = require_roles("SUPPORT_AGENT")


@router.post("/api/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> TaskRead:
    """Submit one operator task (starts `pending`; the runner executes)."""
    return TaskService(session).create_task(payload, created_by="api")


@router.get("/api/tasks", response_model=list[TaskRead])
def list_tasks(
    limit: int = Query(default=50, ge=1, le=200),
    task_status: str | None = Query(default=None, alias="status"),
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> list[TaskRead]:
    """Newest tasks first, optionally filtered to one lifecycle state."""
    return TaskService(session).list_tasks(limit=limit, status=task_status)


@router.get("/api/tasks/{task_id}", response_model=TaskRead)
def get_task(
    task_id: UUID,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> TaskRead:
    """Read one task row (status follows the runner's lifecycle)."""
    return TaskService(session).get_task(task_id)


@router.post("/api/tasks/{task_id}/cancel", response_model=TaskRead)
def cancel_task(
    task_id: UUID,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> TaskRead:
    """Cancel a live task (terminal tasks answer 409)."""
    return TaskService(session).cancel_task(task_id)
