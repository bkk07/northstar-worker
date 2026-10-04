"""Ops customer controller: search with look-alikes (session required)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.commerce.customer import CustomerRead
from app.services.ops.ticket_service import OpsTicketService

router = APIRouter(tags=["ops-customers"])


@router.get("/api/ops/customers", response_model=list[CustomerRead])
def search_customers(
    q: str,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
) -> list[CustomerRead]:
    """Customer search (look-alikes included)."""
    return OpsTicketService(session).search_customers(q)
