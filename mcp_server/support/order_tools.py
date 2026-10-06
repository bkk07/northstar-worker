"""ORDER tools: support-plane reads over Phase 4 orders (spec Phase 7)."""

from app.repositories.orders.order_repository import ShopOrderRepository
from app.services.orders import order_service
from common.northstar_common.config import get_settings
from mcp_server.support import db
from mcp_server.support.envelopes import ok, parse_uuid, run_guarded


def _load(order_id: str):
    """Order row or failure envelope (no auth: support plane)."""
    oid = parse_uuid(order_id, "order_id")
    with db.support_session() as session:
        order = ShopOrderRepository(session).get_by_id(oid)
        if order is None:
            return None, {"ok": False, "code": "NOT_FOUND", "error": "order not found"}
        return order, None


def get_order(order_id: str) -> dict:
    """Full order with items, payment, and live timeline."""
    def _call():
        order, error = _load(order_id)
        if error:
            return error
        with db.support_session() as session:
            detail = order_service.get_order(
                session,
                user_id=str(order.user_id),
                order_id=str(order.id),
                delay_seconds=get_settings().delivery_delay_seconds,
            )
            return ok(order=detail)

    return run_guarded(_call)


def get_order_items(order_id: str) -> dict:
    """Order lines with product snapshots."""
    def _call():
        order, error = _load(order_id)
        if error:
            return error
        with db.support_session() as session:
            lines = ShopOrderRepository(session).list_items(order.id)
            return ok(
                order_number=order.order_number,
                items=[
                    {
                        "product_name": line.product_name_snapshot,
                        "quantity": line.quantity,
                        "unit_price_paise": line.unit_price_paise,
                    }
                    for line in lines
                ],
            )

    return run_guarded(_call)


def get_order_status(order_id: str) -> dict:
    """Stored vs live lifecycle status for verification."""
    def _call():
        order, error = _load(order_id)
        if error:
            return error
        with db.support_session() as session:
            detail = order_service.get_order(
                session,
                user_id=str(order.user_id),
                order_id=str(order.id),
                delay_seconds=get_settings().delivery_delay_seconds,
            )
            return ok(
                order_number=detail["order_number"],
                status=detail["status"],
                payment_status=detail["payment_status"],
                delivered_at=detail["delivered_at"],
            )

    return run_guarded(_call)


def get_order_tracking(order_id: str) -> dict:
    """Delivery timeline plus estimate."""
    def _call():
        order, error = _load(order_id)
        if error:
            return error
        with db.support_session() as session:
            detail = order_service.get_order(
                session,
                user_id=str(order.user_id),
                order_id=str(order.id),
                delay_seconds=get_settings().delivery_delay_seconds,
            )
            return ok(
                order_number=detail["order_number"],
                status=detail["status"],
                timeline=detail["timeline"],
                estimated_delivery=detail["estimated_delivery"],
            )

    return run_guarded(_call)
