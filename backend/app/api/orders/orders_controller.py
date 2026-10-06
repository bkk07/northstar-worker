"""Checkout + orders controller (Phase 4).

Authenticated customers only: `POST /checkout` (mock payment → order),
`GET /orders` (own history), `GET /orders/:id` (tracking detail).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.deps import get_db
from app.schemas.orders import CheckoutCreate, OrderDetail, OrderListItem
from app.services.orders import order_service
from common.northstar_common.config import get_settings

router = APIRouter(tags=["orders"])


def _delay_seconds() -> int:
    """Demo lifecycle speed (spec §10, `DELIVERY_DELAY_SECONDS`)."""
    return get_settings().delivery_delay_seconds


@router.post("/checkout", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
def checkout(
    payload: CheckoutCreate,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Pay (mock SUCCESS) and create the order from the open cart."""
    return order_service.checkout(
        session,
        user_id=str(claims["sub"]),
        shipping_address=payload.shipping_address,
        delay_seconds=_delay_seconds(),
    )


@router.get("/orders", response_model=list[OrderListItem])
def list_orders(
    claims: dict = Depends(get_current_user), session: Session = Depends(get_db)
) -> list[dict]:
    """Own orders, newest first, with live lifecycle status."""
    return order_service.list_orders(
        session, user_id=str(claims["sub"]), delay_seconds=_delay_seconds()
    )


@router.get("/orders/{order_id}", response_model=OrderDetail)
def get_order(
    order_id: str,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Order tracking detail (ownership-checked)."""
    return order_service.get_order(
        session,
        user_id=str(claims["sub"]),
        order_id=order_id,
        delay_seconds=_delay_seconds(),
    )
