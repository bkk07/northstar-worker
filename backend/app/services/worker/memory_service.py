"""Worker memory service: read sourced working memory for a task.

Memory is run-scoped; the endpoint unions the task's runs newest first
so the Control Center shows each fact with provenance, timestamp, and
run ID. There is no cross-task memory.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.worker.memory import MemoryItemRead
from database.models.worker.memory import MemoryItem
from database.models.worker.task import Task, TaskRun


class MemoryService:
    """Read-only memory over `worker.memory_items` (`ns_app` role)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_task(self, task_id: UUID) -> list[MemoryItemRead]:
        """Every memory item across the task's runs, newest first."""
        if self._session.get(Task, task_id) is None:
            raise NotFoundError(f"task {task_id} not found")
        rows = (
            self._session.query(MemoryItem)
            .join(TaskRun, MemoryItem.run_id == TaskRun.id)
            .filter(TaskRun.task_id == task_id)
            .order_by(MemoryItem.created_at.desc(), MemoryItem.id.desc())
            .all()
        )
        return [
            MemoryItemRead(
                id=row.id,
                run_id=row.run_id,
                key=row.key,
                value=dict(row.value or {}),
                source_type=row.source_type,
                source_ref=row.source_ref,
                trust=row.trust,
                confidence=row.confidence,
                created_at=row.created_at,
            )
            for row in rows
        ]
