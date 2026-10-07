"""Worker verification controller: independent proof per run."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.schemas.worker.verification import VerificationRead
from app.services.worker.verification_service import VerificationService

router = APIRouter(tags=["worker-verification"])

_staff = require_roles("SUPPORT_AGENT")


@router.get("/api/tasks/{task_id}/verification", response_model=list[VerificationRead])
def task_verification(
    task_id: UUID,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> list[VerificationRead]:
    """Persisted verifier verdicts across the task's runs, oldest first."""
    return VerificationService(session).results_for_task(task_id)
