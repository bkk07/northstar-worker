"""Task repository: task rows and run attempts (`worker.tasks`, `worker.task_runs`).

The runner owns task lifecycle (transitions validated before writing);
the backend API creates `pending` tasks. One `TaskRun` per attempt —
crash resume starts a new attempt row (Phase 20), never edits history.
"""

from uuid import UUID

from sqlalchemy import func, select

from agent.repositories.base import BaseRepository
from database.models.worker.task import Task, TaskRun


class TaskRepository(BaseRepository[Task]):
    """`ns_runner`-role task/run lifecycle (runner only)."""

    def create_task(
        self,
        text: str,
        mode: str,
        created_by: str,
        scenario_ref: str | None = None,
    ) -> Task:
        """Insert a `pending` task (the runner moves it to `running`)."""
        row = Task(
            text=text,
            mode=mode,
            status="pending",
            current_state="pending",
            scenario_ref=scenario_ref,
            created_by=created_by,
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def get_task(self, task_id: UUID) -> Task | None:
        """Fetch one task (None when absent)."""
        return self.get_by_id(Task, task_id)

    def set_state(self, task: Task, status: str) -> Task:
        """Move a task (caller validates via `transitions.assert_allowed`)."""
        task.status = status
        task.current_state = status
        self.flush()
        return self.refresh(task)

    def create_run(self, task_id: UUID, lease_owner: str, started_at) -> TaskRun:
        """Open the next attempt row for a task (attempts count from 1)."""
        peak = self._session.scalar(
            select(func.max(TaskRun.attempt)).where(TaskRun.task_id == task_id)
        )
        row = TaskRun(
            task_id=task_id,
            attempt=(peak if peak is not None else 0) + 1,
            lease_owner=lease_owner,
            started_at=started_at,
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def finish_run(self, run: TaskRun, ended_at) -> TaskRun:
        """Stamp a run's end (attempt rows stay immutable)."""
        run.ended_at = ended_at
        self.flush()
        return self.refresh(run)
