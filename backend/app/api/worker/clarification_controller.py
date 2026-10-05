"""Worker clarification controller: operator and customer questions."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.worker.clarifications import ClarificationAnswer, ClarificationRead
from app.services.worker.clarification_service import ClarificationService

router = APIRouter(tags=["worker-clarifications"])


@router.get("/api/clarifications", response_model=list[ClarificationRead])
def list_clarifications(
    session: Session = Depends(get_db),
) -> list[ClarificationRead]:
    """Pending clarifications with kind, question, and queue."""
    return ClarificationService(session).list_pending()


@router.post("/api/clarifications/{clarification_id}/answer", response_model=ClarificationRead)
def answer_clarification(
    clarification_id: UUID,
    payload: ClarificationAnswer,
    session: Session = Depends(get_db),
) -> ClarificationRead:
    """Answer once and requeue the parked task (409 unless pending)."""
    return ClarificationService(session).answer(clarification_id, payload)
