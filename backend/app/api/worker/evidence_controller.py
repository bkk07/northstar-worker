"""Worker evidence controller: terminal packets and screenshot index."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.schemas.worker.evidence import EvidencePacketRead, ScreenshotRead
from app.services.worker.evidence_service import EvidenceService

router = APIRouter(tags=["worker-evidence"])

_staff = require_roles("SUPPORT_AGENT")


@router.get("/api/tasks/{task_id}/evidence", response_model=EvidencePacketRead)
def task_evidence(
    task_id: UUID,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> EvidencePacketRead:
    """Latest terminal packet (404 when the task never reached terminal)."""
    return EvidenceService(session).latest_packet(task_id)


@router.get("/api/tasks/{task_id}/evidence/screenshots", response_model=list[ScreenshotRead])
def task_screenshots(
    task_id: UUID,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> list[ScreenshotRead]:
    """Screenshot index for the task's evidence trail, oldest first."""
    return EvidenceService(session).screenshots_for_task(task_id)
