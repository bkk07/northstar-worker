"""Worker clarification service: answer parked questions, requeue tasks.

Operator clarifications re-enter the contract compiler with the answer
recorded; customer-information requests park on the customer until a
reply exists. Answering moves the task back to `running`.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.worker.clarifications import ClarificationAnswer, ClarificationRead
from database.models.worker.flow import Clarification
from database.models.worker.task import Task

_REQUEUE_FROM = frozenset({"waiting_for_clarification", "waiting_on_customer"})


class ClarificationService:
    """Operator/customer question queue over `worker.clarifications`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_pending(self) -> list[ClarificationRead]:
        """Pending clarifications, oldest first."""
        rows = (
            self._session.query(Clarification)
            .filter(Clarification.status == "pending")
            .order_by(Clarification.created_at)
            .all()
        )
        return [self._to_dto(row) for row in rows]

    def get_clarification(self, clarification_id: UUID) -> ClarificationRead:
        """One clarification (404 when absent)."""
        return self._to_dto(self._get(clarification_id))

    def answer(self, clarification_id: UUID, payload: ClarificationAnswer) -> ClarificationRead:
        """Answer once and requeue the task (409 unless pending)."""
        row = self._get(clarification_id)
        if row.status != "pending":
            raise ConflictError(f"clarification {clarification_id} is already {row.status}")
        row.status = "answered"
        row.answer = payload.answer
        row.answered_by = payload.answered_by
        task = self._session.get(Task, row.task_id)
        if task is not None and task.status in _REQUEUE_FROM:
            task.status = "running"
            task.current_state = "running"
        self._session.commit()
        self._session.refresh(row)
        return self._to_dto(row)

    def _get(self, clarification_id: UUID) -> Clarification:
        row = self._session.get(Clarification, clarification_id)
        if row is None:
            raise NotFoundError(f"clarification {clarification_id} not found")
        return row

    @staticmethod
    def _to_dto(row: Clarification) -> ClarificationRead:
        return ClarificationRead(
            id=row.id,
            task_id=row.task_id,
            kind=row.kind,
            question=row.question,
            answer=row.answer,
            answered_by=row.answered_by,
            status=row.status,
            created_at=row.created_at,
        )
