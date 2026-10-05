"""Worker memory controller: sourced working memory for a task."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.worker.memory import MemoryItemRead
from app.services.worker.memory_service import MemoryService

router = APIRouter(tags=["worker-memory"])


@router.get("/api/tasks/{task_id}/memory", response_model=list[MemoryItemRead])
def list_task_memory(task_id: UUID, session: Session = Depends(get_db)) -> list[MemoryItemRead]:
    """Working memory with fact, provenance, timestamp, and run ID."""
    return MemoryService(session).list_for_task(task_id)
