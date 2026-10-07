"""Worker approval controller: the operator decision queue."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.schemas.worker.approvals import ApprovalDecide, ApprovalRead
from app.services.worker.approval_service import ApprovalService

router = APIRouter(tags=["worker-approvals"])

_staff = require_roles("SUPPORT_AGENT")


@router.get("/api/approvals", response_model=list[ApprovalRead])
def list_approvals(
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> list[ApprovalRead]:
    """Pending approvals with action, params, reason, and rule."""
    return ApprovalService(session).list_pending()


@router.post("/api/approvals/{approval_id}/approve", response_model=ApprovalRead)
def approve_approval(
    approval_id: UUID,
    payload: ApprovalDecide,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> ApprovalRead:
    """Approve once and requeue the parked task (409 unless pending)."""
    return ApprovalService(session).approve(approval_id, payload)


@router.post("/api/approvals/{approval_id}/reject", response_model=ApprovalRead)
def reject_approval(
    approval_id: UUID,
    payload: ApprovalDecide,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> ApprovalRead:
    """Reject once and requeue the task (the graph finalizes BLOCKED)."""
    return ApprovalService(session).reject(approval_id, payload)
