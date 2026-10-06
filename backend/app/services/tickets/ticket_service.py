"""Phase 5 raise-ticket + conversation service.

Customers create OPEN tickets (optionally linked to one of their Phase 4
orders) and can follow up while the ticket is unresolved. Support replies,
AI, and resolution arrive in later phases. `generate_ticket_number` and the
validators are pure (unit-testable).
"""

import datetime
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
from app.repositories.orders.order_repository import ShopOrderRepository
from app.repositories.tickets.ticket_repository import CustomerTicketRepository
from app.services.orders.order_service import resolve_status
from app.services.products import product_service
from common.northstar_common.config import get_settings
from database.models.biz.customer_ticket import (
    CATEGORIES,
    PRIORITIES,
    SENDER_CUSTOMER,
    TICKET_CLOSED,
    TICKET_RESOLVED,
)


def generate_ticket_number() -> str:
    """Human ticket number (`TKT-XXXXXX`, unique-guarded by DB)."""
    return f"TKT-{uuid.uuid4().hex[:6].upper()}"


def normalize_category(category: str) -> str:
    """Uppercase category or raise (pure)."""
    upper = category.strip().upper()
    if upper not in CATEGORIES:
        raise UnprocessableError(f"unknown category (use one of: {', '.join(CATEGORIES)})")
    return upper


def normalize_priority(priority: str) -> str:
    """Uppercase priority or raise (pure)."""
    upper = priority.strip().upper()
    if upper not in PRIORITIES:
        raise UnprocessableError(f"unknown priority (use one of: {', '.join(PRIORITIES)})")
    return upper


def _order_summary(order, item_count: int) -> dict:
    now = datetime.datetime.now(datetime.UTC)
    delay = get_settings().delivery_delay_seconds
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "status": resolve_status(order.ordered_at, now, delay_seconds=delay),
        "total_display": product_service.format_price(order.total_paise),
        "item_count": item_count,
    }


def _serialize_detail(ticket, messages: list[dict], related_order: dict | None) -> dict:
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
        "related_order": related_order,
        "messages": messages,
    }


def _serialize_message(row) -> dict:
    return {
        "id": str(row.id),
        "sender_type": row.sender_type,
        "message": row.message,
        "created_at": row.created_at.isoformat(),
    }


def _owned_ticket(
    session: Session, *, user_id: str, ticket_id: str
):
    """Ticket by id, or raise (ownership-checked)."""
    repo = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = repo.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")
    if str(ticket.user_id) != str(user_id):
        raise ForbiddenError("ticket belongs to another customer")
    return repo, ticket


def create_ticket(
    session: Session,
    *,
    user_id: str,
    subject: str,
    category: str,
    description: str,
    order_id: str | None,
    priority: str,
) -> dict:
    """Raise an OPEN ticket, seeding the conversation with the description."""
    clean_category = normalize_category(category)
    clean_priority = normalize_priority(priority)
    order_uuid = None
    related_order = None
    if order_id is not None:
        order_repo = ShopOrderRepository(session)
        try:
            order_uuid = uuid.UUID(order_id)
        except ValueError:
            raise NotFoundError("order not found") from None
        order = order_repo.get_by_id(order_uuid)
        if order is None:
            raise NotFoundError("order not found")
        if str(order.user_id) != str(user_id):
            raise ForbiddenError("order belongs to another customer")
        related_order = _order_summary(order, len(order_repo.list_items(order.id)))

    repo = CustomerTicketRepository(session)
    ticket = repo.create_ticket(
        user_id=user_id,
        order_id=order_uuid,
        ticket_number=generate_ticket_number(),
        subject=subject.strip(),
        description=description.strip(),
        category=clean_category,
        priority=clean_priority,
    )
    first = repo.add_message(
        ticket_id=ticket.id,
        sender_type=SENDER_CUSTOMER,
        sender_id=user_id,
        message=description.strip(),
    )
    session.commit()
    session.refresh(ticket)
    return _serialize_detail(ticket, [_serialize_message(first)], related_order)


def list_tickets(session: Session, *, user_id: str) -> list[dict]:
    """Own tickets, newest first."""
    repo = CustomerTicketRepository(session)
    order_repo = ShopOrderRepository(session)
    out = []
    for ticket in repo.list_by_user(user_id):
        order_number = None
        if ticket.order_id is not None:
            order = order_repo.get_by_id(ticket.order_id)
            order_number = order.order_number if order else None
        out.append(
            {
                "id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "subject": ticket.subject,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "order_number": order_number,
                "message_count": repo.count_messages(ticket.id),
                "created_at": ticket.created_at.isoformat(),
            }
        )
    return out


def get_ticket(session: Session, *, user_id: str, ticket_id: str) -> dict:
    """Ticket conversation with related-order context (ownership-checked)."""
    repo, ticket = _owned_ticket(session, user_id=user_id, ticket_id=ticket_id)
    related_order = None
    if ticket.order_id is not None:
        order_repo = ShopOrderRepository(session)
        order = order_repo.get_by_id(ticket.order_id)
        if order is not None:
            related_order = _order_summary(order, len(order_repo.list_items(order.id)))
    messages = [_serialize_message(m) for m in repo.list_messages(ticket.id)]
    return _serialize_detail(ticket, messages, related_order)


def add_message(session: Session, *, user_id: str, ticket_id: str, message: str) -> dict:
    """Customer follow-up (rejected once resolved/closed)."""
    repo, ticket = _owned_ticket(session, user_id=user_id, ticket_id=ticket_id)
    if ticket.status in (TICKET_RESOLVED, TICKET_CLOSED):
        raise UnprocessableError("ticket is already resolved")
    text = message.strip()
    if not text:
        raise UnprocessableError("message is empty")
    row = repo.add_message(
        ticket_id=ticket.id,
        sender_type=SENDER_CUSTOMER,
        sender_id=user_id,
        message=text,
    )
    ticket.updated_at = datetime.datetime.now(datetime.UTC)
    session.commit()
    session.refresh(row)
    return _serialize_message(row)
