"""Worker task controller: minimal create / read for the task queue."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.worker.tasks import TaskCreate, TaskRead
from app.services.worker.task_service import TaskService

router = APIRouter(tags=["worker-tasks"])


@router.post("/api/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, session: Session = Depends(get_db)) -> TaskRead:
    """Submit one operator task (starts `pending`; the runner executes)."""
    return TaskService(session).create_task(payload, created_by="api")


@router.get("/api/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: UUID, session: Session = Depends(get_db)) -> TaskRead:
    """Read one task row (status follows the runner's lifecycle)."""
    return TaskService(session).get_task(task_id)
