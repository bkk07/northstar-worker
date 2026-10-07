"""Phase 6 support console service: dashboard stats, ticket queue, full
ticket context, and manual actions (reply, internal note, resolve, escalate).

All endpoints are staff-only (`SUPPORT_AGENT`, enforced in the controller).
AI solve, approvals, and live activity arrive in Phases 8-9; the dashboard
therefore reports `waiting`/`ai_processing` as 0 until then. `summarize_stats`
and `ensure_action_allowed` are pure (unit-testable).
"""

import datetime
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnprocessableError
from app.repositories.auth.user_repository import UserRepository
from app.repositories.orders.order_repository import ShopOrderRepository
from app.repositories.products.product_repository import ProductRepository
from app.repositories.tickets.ticket_repository import CustomerTicketRepository
from app.services.orders.order_service import resolve_status
from app.services.products import product_service
from app.services.tickets.ticket_service import normalize_category
from common.northstar_common.config import get_settings
from database.models.biz.customer_ticket import (
    PRIORITIES,
    SENDER_AI_AGENT,
    SENDER_SUPPORT_AGENT,
    SENDER_SYSTEM,
    TICKET_CLOSED,
    TICKET_ESCALATED,
    TICKET_OPEN,
    TICKET_RESOLVED,
)

AGENT_SENDERS = (SENDER_AI_AGENT, SENDER_SUPPORT_AGENT, SENDER_SYSTEM)

ACTIONABLE = (TICKET_OPEN, TICKET_ESCALATED)
TERMINAL = (TICKET_RESOLVED, TICKET_CLOSED)


def summarize_stats(by_status: dict[str, int]) -> dict:
    """Dashboard cards from per-status counts (pure)."""
    from database.models.biz.customer_ticket import (
        TICKET_AI_PROCESSING,
        TICKET_WAITING_FOR_CUSTOMER,
        TICKET_WAITING_FOR_HUMAN,
    )

    open_count = by_status.get(TICKET_OPEN, 0)
    ai_processing = by_status.get(TICKET_AI_PROCESSING, 0)
    waiting_human = by_status.get(TICKET_WAITING_FOR_HUMAN, 0)
    waiting_customer = by_status.get(TICKET_WAITING_FOR_CUSTOMER, 0)
    escalated = by_status.get(TICKET_ESCALATED, 0)
    resolved = by_status.get(TICKET_RESOLVED, 0) + by_status.get(TICKET_CLOSED, 0)
    return {
        "by_status": {
            TICKET_OPEN: open_count,
            "AI_PROCESSING": ai_processing,
            "WAITING_FOR_CUSTOMER": waiting_customer,
            "WAITING_FOR_HUMAN": waiting_human,
            TICKET_ESCALATED: escalated,
            TICKET_RESOLVED: by_status.get(TICKET_RESOLVED, 0),
            TICKET_CLOSED: by_status.get(TICKET_CLOSED, 0),
        },
        "summary": {
            "open": open_count,
            "in_progress": escalated + ai_processing,
            "waiting": waiting_human + waiting_customer,
            "resolved": resolved,
        },
    }


def ensure_action_allowed(status: str, action: str) -> None:
    """Guard manual actions against terminal tickets (pure)."""
    if status in TERMINAL:
        raise UnprocessableError(f"ticket is already {status.lower()} ({action} rejected)")


def _staff_uuid(staff_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(staff_id)
    except ValueError:
        return None


def dashboard_stats(session: Session) -> dict:
    """Ticket counts for the support dashboard."""
    return summarize_stats(CustomerTicketRepository(session).count_by_status())


def list_queue(
    session: Session,
    *,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """Ticket queue rows with customer + order + count context."""
    repo = CustomerTicketRepository(session)
    users = UserRepository(session)
    orders = ShopOrderRepository(session)
    out = []
    for ticket in repo.list_all(status=status, priority=priority, search=search):
        customer = users.get_by_id(ticket.user_id)
        order_number = None
        if ticket.order_id is not None:
            order = orders.get_by_id(ticket.order_id)
            order_number = order.order_number if order else None
        out.append(
            {
                "id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "subject": ticket.subject,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "customer_name": customer.name if customer else "Unknown",
                "customer_email": customer.email if customer else "",
                "order_number": order_number,
                "message_count": repo.count_messages(ticket.id, include_internal=True),
                "created_at": ticket.created_at.isoformat(),
            }
        )
    return out


def _serialize_message(row) -> dict:
    return {
        "id": str(row.id),
        "sender_type": row.sender_type,
        "message": row.message,
        "is_internal": bool(row.is_internal),
        "created_at": row.created_at.isoformat(),
    }


def get_ticket_detail(session: Session, *, ticket_id: str) -> dict:
    """Full console context: conversation, customer, orders, policies."""
    repo = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = repo.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")

    users = UserRepository(session)
    customer = users.get_by_id(ticket.user_id)
    orders = ShopOrderRepository(session)
    products = ProductRepository(session)
    delay = get_settings().delivery_delay_seconds
    now = datetime.datetime.now(datetime.UTC)

    related_order = None
    policies: list[dict] = []
    if ticket.order_id is not None:
        order = orders.get_by_id(ticket.order_id)
        if order is not None:
            lines = orders.list_items(order.id)
            items = []
            for line in lines:
                items.append(
                    {
                        "product_name": line.product_name_snapshot,
                        "quantity": line.quantity,
                        "unit_price_paise": line.unit_price_paise,
                        "line_total_paise": line.quantity * line.unit_price_paise,
                    }
                )
                product = products.get_by_id(line.product_id)
                policy = products.get_policy(line.product_id) if product else None
                summary = product_service.summarize_policy(policy)
                policies.append(
                    {
                        "product_name": line.product_name_snapshot,
                        "summary": summary["summary"],
                        "return_allowed": summary["return_allowed"],
                        "refund_allowed": summary["refund_allowed"],
                        "cancellation_allowed": summary["cancellation_allowed"],
                    }
                )
            payment = orders.get_payment(order.id)
            related_order = {
                "id": str(order.id),
                "order_number": order.order_number,
                "status": resolve_status(order.ordered_at, now, delay_seconds=delay),
                "total_display": product_service.format_price(order.total_paise),
                "payment_status": order.payment_status,
                "payment_reference": payment.payment_reference if payment else None,
                "shipping_address": order.shipping_address,
                "ordered_at": order.ordered_at.isoformat(),
                "items": items,
            }

    recent_orders = []
    for order in orders.list_by_user(ticket.user_id)[:5]:
        recent_orders.append(
            {
                "id": str(order.id),
                "order_number": order.order_number,
                "status": resolve_status(order.ordered_at, now, delay_seconds=delay),
                "total_display": product_service.format_price(order.total_paise),
                "ordered_at": order.ordered_at.isoformat(),
            }
        )

    previous_tickets = [
        {
            "id": str(t.id),
            "ticket_number": t.ticket_number,
            "subject": t.subject,
            "status": t.status,
        }
        for t in repo.list_by_user(ticket.user_id)
        if t.id != ticket.id
    ][:5]

    return {
        "id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "resolution": ticket.resolution,
        "created_at": ticket.created_at.isoformat(),
        "customer": {
            "id": str(ticket.user_id),
            "name": customer.name if customer else "Unknown",
            "email": customer.email if customer else "",
            "created_at": customer.created_at.isoformat() if customer else None,
        },
        "related_order": related_order,
        "policies": policies,
        "recent_orders": recent_orders,
        "previous_tickets": previous_tickets,
        "messages": [
            _serialize_message(m) for m in repo.list_messages(ticket.id, include_internal=True)
        ],
    }


def _staff_reply(
    session: Session,
    *,
    staff_id: str,
    ticket_id: str,
    message: str,
    is_internal: bool,
) -> dict:
    repo = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = repo.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")
    text = message.strip()
    if not text:
        raise UnprocessableError("message is empty")
    row = repo.add_message(
        ticket_id=ticket.id,
        sender_type=SENDER_SUPPORT_AGENT,
        sender_id=_staff_uuid(staff_id),
        message=text,
        is_internal=is_internal,
    )
    ticket.updated_at = datetime.datetime.now(datetime.UTC)
    session.commit()
    session.refresh(row)
    return _serialize_message(row)


def reply(session: Session, *, staff_id: str, ticket_id: str, message: str) -> dict:
    """Manual customer-visible reply (blocked once resolved/closed)."""
    repo = CustomerTicketRepository(session)
    try:
        ticket = repo.get_by_id(uuid.UUID(ticket_id))
    except ValueError:
        raise NotFoundError("ticket not found") from None
    if ticket is None:
        raise NotFoundError("ticket not found")
    ensure_action_allowed(ticket.status, "reply")
    return _staff_reply(session, staff_id=staff_id, ticket_id=ticket_id, message=message,
                        is_internal=False)


def add_note(session: Session, *, staff_id: str, ticket_id: str, message: str) -> dict:
    """Internal note (never shown to the customer)."""
    repo = CustomerTicketRepository(session)
    try:
        ticket = repo.get_by_id(uuid.UUID(ticket_id))
    except ValueError:
        raise NotFoundError("ticket not found") from None
    if ticket is None:
        raise NotFoundError("ticket not found")
    ensure_action_allowed(ticket.status, "note")
    return _staff_reply(session, staff_id=staff_id, ticket_id=ticket_id, message=message,
                        is_internal=True)


def resolve(session: Session, *, staff_id: str, ticket_id: str, resolution: str) -> dict:
    """Resolve with a resolution note + system audit message."""
    repo = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = repo.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")
    ensure_action_allowed(ticket.status, "resolve")
    text = resolution.strip()
    if len(text) < 5:
        raise UnprocessableError("resolution needs at least 5 characters")
    now = datetime.datetime.now(datetime.UTC)
    ticket.status = TICKET_RESOLVED
    ticket.resolution = text
    ticket.resolved_at = now
    ticket.updated_at = now
    repo.add_message(
        ticket_id=ticket.id,
        sender_type=SENDER_SYSTEM,
        sender_id=_staff_uuid(staff_id),
        message=f"Ticket resolved by support: {text}",
    )
    session.commit()
    session.refresh(ticket)
    return {"id": str(ticket.id), "status": ticket.status, "resolution": ticket.resolution}


def escalate(session: Session, *, staff_id: str, ticket_id: str, reason: str | None) -> dict:
    """Escalate an actionable ticket + system audit message."""
    repo = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = repo.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")
    ensure_action_allowed(ticket.status, "escalate")
    if ticket.status == TICKET_ESCALATED:
        raise UnprocessableError("ticket is already escalated")
    ticket.status = TICKET_ESCALATED
    ticket.updated_at = datetime.datetime.now(datetime.UTC)
    suffix = f": {reason.strip()}" if reason and reason.strip() else ""
    note = f"Ticket escalated by support{suffix}."
    repo.add_message(
        ticket_id=ticket.id,
        sender_type=SENDER_SYSTEM,
        sender_id=_staff_uuid(staff_id),
        message=note,
    )
    session.commit()
    session.refresh(ticket)
    return {"id": str(ticket.id), "status": ticket.status}


def add_agent_message(
    session: Session, *, ticket_id: str, sender_type: str, message: str
) -> dict:
    """Agent-plane message (Phase 7 MCP): AI / staff / system senders only."""
    if sender_type not in AGENT_SENDERS:
        raise UnprocessableError(
            f"unknown sender (use one of: {', '.join(AGENT_SENDERS)})"
        )
    repo = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = repo.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")
    ensure_action_allowed(ticket.status, "message")
    text = message.strip()
    if not text:
        raise UnprocessableError("message is empty")
    row = repo.add_message(
        ticket_id=ticket.id, sender_type=sender_type, sender_id=None, message=text
    )
    ticket.updated_at = datetime.datetime.now(datetime.UTC)
    session.commit()
    session.refresh(row)
    return _serialize_message(row)


def search_knowledge(session: Session, *, q: str, limit: int = 10) -> list[dict]:
    """Substring search over products, product policies, and policy rules."""
    from app.repositories.commerce.policy_repository import PolicyRepository
    from app.services.commerce.catalog_service import summarize_rule

    needle = q.strip().lower()
    hits: list[dict] = []
    products = ProductRepository(session)
    for product in products.list_active():
        haystack = f"{product.name} {product.description} {product.category} {product.brand}"
        if needle in haystack.lower():
            hits.append(
                {
                    "source": "product",
                    "ref": product.slug,
                    "snippet": f"{product.name} ({product.brand}) — "
                    f"{product_service.format_price(product.price_paise)}",
                }
            )
    for product in products.list_active():
        policy = products.get_policy(product.id)
        if policy and needle in (policy.policy_text or "").lower():
            hits.append(
                {
                    "source": "product_policy",
                    "ref": product.slug,
                    "snippet": policy.policy_text,
                }
            )
    for rule in PolicyRepository(session).list_all():
        if needle in rule.rule_key.lower():
            hits.append(
                {
                    "source": "policy_rule",
                    "ref": rule.rule_key,
                    "snippet": summarize_rule(rule.rule_key, rule.params or {}),
                }
            )
    return hits[: max(1, min(limit, 25))]


def update_ticket(
    session: Session,
    *,
    ticket_id: str,
    priority: str | None = None,
    category: str | None = None,
) -> dict:
    """Agent-safe field update: priority and/or category only."""
    repo = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = repo.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")
    if priority is not None:
        upper = priority.strip().upper()
        if upper not in PRIORITIES:
            raise UnprocessableError(f"unknown priority (use one of: {', '.join(PRIORITIES)})")
        ticket.priority = upper
    if category is not None:
        ticket.category = normalize_category(category)
    ticket.updated_at = datetime.datetime.now(datetime.UTC)
    session.commit()
    session.refresh(ticket)
    return {
        "id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "priority": ticket.priority,
        "category": ticket.category,
        "status": ticket.status,
    }

