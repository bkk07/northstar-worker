"""Ops refund controller: idempotent refund commits."""

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.commerce.financial import RefundRead
from app.schemas.ops.mutations import RefundCreate
from app.services.ops.refund_service import RefundService

router = APIRouter(tags=["ops-refunds"])


@router.post("/api/ops/refunds", response_model=RefundRead)
def create_refund(
    payload: RefundCreate,
    response: Response,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> RefundRead:
    """Commit a refund (201) or replay it (200) for a known key."""
    dto, created = RefundService(session).create(payload, idempotency_key)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return dto
