"""Worker task service: minimal task create / read / cancel (`ns_app` role)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.worker.tasks import TaskCreate, TaskRead
from database.models.worker.task import Task

_ALLOWED_CANCEL_FROM = frozenset(
    {
        "pending",
        "running",
        "waiting_for_approval",
        "waiting_for_clarification",
        "waiting_on_customer",
    }
)


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

    def list_tasks(self, limit: int = 50, status: str | None = None) -> list[TaskRead]:
        """Newest tasks first, optionally filtered to one lifecycle state."""
        query = self._session.query(Task).order_by(Task.created_at.desc(), Task.id.desc())
        if status:
            query = query.filter(Task.status == status)
        return [self._to_dto(row) for row in query.limit(max(limit, 1)).all()]

    def get_task(self, task_id: UUID) -> TaskRead:
        """One task (404 when absent)."""
        row = self._session.get(Task, task_id)
        if row is None:
            raise NotFoundError(f"task {task_id} not found")
        return self._to_dto(row)

    def cancel_task(self, task_id: UUID) -> TaskRead:
        """Cancel a live task (409 when already terminal)."""
        row = self._session.get(Task, task_id)
        if row is None:
            raise NotFoundError(f"task {task_id} not found")
        if row.status not in _ALLOWED_CANCEL_FROM:
            raise ConflictError(f"task {task_id} is already {row.status}")
        row.status = "cancelled"
        row.current_state = "cancelled"
        self._session.commit()
        self._session.refresh(row)
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
