"""POLICY tools: eligibility reports over orders + product policies.

Read-only: the agent checks these before proposing an action, and Phase 9
re-checks them during verification.
"""

from app.repositories.orders.order_repository import ShopOrderRepository
from app.services.actions import action_service
from mcp_server.support import db
from mcp_server.support.envelopes import fail, ok, parse_uuid, run_guarded


def _report(action_type: str, order_id: str) -> dict:
    def _call():
        oid = parse_uuid(order_id, "order_id")
        with db.support_session() as session:
            order = ShopOrderRepository(session).get_by_id(oid)
            if order is None:
                return fail("order not found", code="NOT_FOUND")
            report = action_service.eligibility(
                session, action_type=action_type, order_id=str(order.id)
            )
            return ok(
                action_type=action_type,
                order_number=order.order_number,
                eligible=report["eligible"],
                reasons=report["reasons"],
            )

    return run_guarded(_call)


def check_refund_eligibility(order_id: str) -> dict:
    """Can this order be (further) refunded under policy?"""
    return _report("REFUND", order_id)


def check_return_eligibility(order_id: str) -> dict:
    """Can this order be returned under policy?"""
    return _report("RETURN", order_id)


def check_replacement_eligibility(order_id: str) -> dict:
    """Can this order get a replacement under policy?"""
    return _report("REPLACE", order_id)


def check_cancellation_eligibility(order_id: str) -> dict:
    """Can this order still be cancelled?"""
    return _report("CANCEL", order_id)
