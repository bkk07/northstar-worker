"""Worker task service: minimal task create / read (`ns_app` role)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.worker.tasks import TaskCreate, TaskRead
from database.models.worker.task import Task


class TaskService:
    """Operator task queue over `worker.tasks` (lifecycle: the runner)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_task(self, payload: TaskCreate, created_by: str) -> TaskRead:
        """Insert a `pending` task (the runner moves it to `running`)."""
        row = Task(
            text=payload.text,
            mode=payload.mode,
            status="pending",
            current_state="pending",
            scenario_ref=payload.scenario_ref,
            created_by=created_by,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_dto(row)

    def get_task(self, task_id: UUID) -> TaskRead:
        """One task (404 when absent)."""
        row = self._session.get(Task, task_id)
        if row is None:
            raise NotFoundError(f"task {task_id} not found")
        return self._to_dto(row)

    @staticmethod
    def _to_dto(row: Task) -> TaskRead:
        return TaskRead(
            id=row.id,
            text=row.text,
            mode=row.mode,
            status=row.status,
            current_state=row.current_state,
            scenario_ref=row.scenario_ref,
            created_by=row.created_by,
            created_at=row.created_at,
        )
