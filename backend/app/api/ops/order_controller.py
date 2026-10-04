"""Ops order controller: order lookup (session required)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.commerce.order import OrderRead
from app.services.commerce.order_service import OrderService

router = APIRouter(tags=["ops-orders"])


@router.get("/api/ops/orders/{order_code}", response_model=OrderRead)
def get_order(
    order_code: str,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
) -> OrderRead:
    """Order detail with items."""
    return OrderService(session).get_by_code(order_code)
