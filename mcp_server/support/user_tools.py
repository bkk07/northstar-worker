"""USER tools: support-plane reads over `biz.app_users` (spec Phase 7)."""

from app.repositories.auth.user_repository import UserRepository
from app.repositories.orders.order_repository import ShopOrderRepository
from app.repositories.tickets.ticket_repository import CustomerTicketRepository
from mcp_server.support import db
from mcp_server.support.envelopes import fail, ok, parse_uuid, run_guarded


def get_user(user_id: str) -> dict:
    """Customer profile by app-user id, with order/ticket counts."""
    def _call():
        uid = parse_uuid(user_id, "user_id")
        with db.support_session() as session:
            user = UserRepository(session).get_by_id(uid)
            if user is None:
                return fail("user not found", code="NOT_FOUND")
            orders = ShopOrderRepository(session).list_by_user(uid)
            tickets = CustomerTicketRepository(session).list_by_user(uid)
            return ok(
                user={
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "order_count": len(orders),
                    "ticket_count": len(tickets),
                }
            )

    return run_guarded(_call)


def get_user_orders(user_id: str) -> dict:
    """Order summaries for one customer, newest first."""
    def _call():
        uid = parse_uuid(user_id, "user_id")
        with db.support_session() as session:
            if UserRepository(session).get_by_id(uid) is None:
                return fail("user not found", code="NOT_FOUND")
            orders = ShopOrderRepository(session).list_by_user(uid)
            return ok(
                orders=[
                    {"id": str(o.id), "order_number": o.order_number, "status": o.status}
                    for o in orders
                ]
            )

    return run_guarded(_call)


def get_user_tickets(user_id: str) -> dict:
    """Ticket summaries for one customer, newest first."""
    def _call():
        uid = parse_uuid(user_id, "user_id")
        with db.support_session() as session:
            if UserRepository(session).get_by_id(uid) is None:
                return fail("user not found", code="NOT_FOUND")
            tickets = CustomerTicketRepository(session).list_by_user(uid)
            return ok(
                tickets=[
                    {
                        "id": str(t.id),
                        "ticket_number": t.ticket_number,
                        "subject": t.subject,
                        "category": t.category,
                        "status": t.status,
                    }
                    for t in tickets
                ]
            )

    return run_guarded(_call)
