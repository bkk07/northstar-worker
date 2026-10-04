"""Ops replacement controller: idempotent replacement commits."""

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.commerce.financial import ReplacementRead
from app.schemas.ops.mutations import ReplacementCreate
from app.services.ops.replacement_service import ReplacementService

router = APIRouter(tags=["ops-replacements"])


@router.post("/api/ops/replacements", response_model=ReplacementRead)
def create_replacement(
    payload: ReplacementCreate,
    response: Response,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> ReplacementRead:
    """Commit a replacement (201) or replay it (200) for a known key."""
    dto, created = ReplacementService(session).create(payload, idempotency_key)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return dto
