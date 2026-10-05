"""Worker verification service: independent proof per run.

Verdicts are persisted by the verifier adapter (`worker
.verification_results`); this service exposes them per task so the
packet — and the operator — can cite the proof behind every DONE.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.worker.verification import VerificationRead
from database.models.worker.evidence import VerificationResult
from database.models.worker.task import Task, TaskRun


class VerificationService:
    """Read-only verdicts over `worker.verification_results` (`ns_app`)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def results_for_task(self, task_id: UUID) -> list[VerificationRead]:
        """Every persisted verdict across the task's runs, oldest first."""
        if self._session.get(Task, task_id) is None:
            raise NotFoundError(f"task {task_id} not found")
        rows = (
            self._session.query(VerificationResult)
            .join(TaskRun, VerificationResult.run_id == TaskRun.id)
            .filter(TaskRun.task_id == task_id)
            .order_by(VerificationResult.computed_at.asc(), VerificationResult.id.asc())
            .all()
        )
        return [
            VerificationRead(
                id=row.id,
                run_id=row.run_id,
                verdict=row.verdict,
                invariants=dict(row.invariants or {}),
                diff=dict(row.diff or {}),
                computed_at=row.computed_at,
            )
            for row in rows
        ]
