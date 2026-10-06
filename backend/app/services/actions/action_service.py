"""Phase 7 mock actions: eligibility checks + idempotent execution.

Eligibility mirrors the per-product policies (Phase 3) and the mock
lifecycle (Phase 4): cancel only while PROCESSING and cancellable,
refund against a SUCCESS payment within policy, return/replace after
delivery inside the product windows. Every execution writes one
`biz.shop_actions` row keyed by `mutation_key` (retries collide → 409),
mutates the order for cancel/return, and posts a SYSTEM audit message when
a ticket is linked — so Phase 9 can execute → verify by re-reading.

`check_*` eligibility helpers are pure (unit-testable); they take plain
policy/window inputs, never rows.
"""

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.repositories.orders.order_repository import ShopOrderRepository
from app.repositories.products.product_repository import ProductRepository
from app.repositories.tickets.ticket_repository import CustomerTicketRepository
from app.services.orders.order_service import resolve_status
from common.northstar_common.config import get_settings
from database.models.biz.customer_ticket import SENDER_SYSTEM
from database.models.biz.shop_action import (
    ACTION_CANCEL,
    ACTION_DONE,
    ACTION_REFUND,
    ACTION_REPLACE,
    ACTION_RETURN,
    ShopAction,
)
from database.models.biz.shop_order import (
    ORDER_CANCELLED,
    ORDER_DELIVERED,
    ORDER_PROCESSING,
    ORDER_RETURNED,
    ORDER_TERMINAL,
)

ACTION_TYPES = (ACTION_REFUND, ACTION_RETURN, ACTION_REPLACE, ACTION_CANCEL)


def _days_since(start: datetime.datetime, now: datetime.datetime) -> float:
    return (now - start).total_seconds() / 86400.0


def check_cancellation(
    *, status: str, cancellable: bool, has_cancel_action: bool
) -> dict:
    """Cancel eligibility (pure): live PROCESSING order, policy allows, unused."""
    reasons = []
    if status != ORDER_PROCESSING:
        reasons.append(f"order is {status}, only PROCESSING orders can cancel")
    if not cancellable:
        reasons.append("product policy forbids cancellation")
    if has_cancel_action:
        reasons.append("order already cancelled")
    return {"eligible": not reasons, "reasons": reasons}


def check_refund(
    *,
    payment_status: str,
    refund_allowed: bool,
    total_paise: int,
    already_refunded_paise: int,
) -> dict:
    """Refund eligibility (pure): paid order, policy allows, amount remains."""
    reasons = []
    if payment_status != "SUCCESS":
        reasons.append(f"payment is {payment_status}, only SUCCESS payments refund")
    if not refund_allowed:
        reasons.append("product policy forbids refunds")
    if already_refunded_paise >= total_paise:
        reasons.append("order already fully refunded")
    return {"eligible": not reasons, "reasons": reasons}


def _window_check(
    *,
    kind: str,
    delivered_at: datetime.datetime | None,
    now: datetime.datetime,
    window_days: int,
    allowed: bool,
    already_done: bool,
) -> dict:
    reasons = []
    if not allowed:
        reasons.append(f"product policy forbids {kind}")
    if delivered_at is None:
        reasons.append(f"order not delivered yet ({kind} needs delivery)")
    elif _days_since(delivered_at, now) > window_days:
        reasons.append(f"outside the {window_days}-day {kind} window")
    if already_done:
        reasons.append(f"{kind} already executed for this order")
    return {"eligible": not reasons, "reasons": reasons}


def check_return(
    *,
    delivered_at: datetime.datetime | None,
    now: datetime.datetime,
    window_days: int,
    allowed: bool,
    already_done: bool,
) -> dict:
    """Return eligibility (pure)."""
    return _window_check(
        kind="return",
        delivered_at=delivered_at,
        now=now,
        window_days=window_days,
        allowed=allowed,
        already_done=already_done,
    )


def check_replacement(
    *,
    delivered_at: datetime.datetime | None,
    now: datetime.datetime,
    window_days: int,
    allowed: bool,
    already_done: bool,
) -> dict:
    """Replacement eligibility (pure)."""
    return _window_check(
        kind="replacement",
        delivered_at=delivered_at,
        now=now,
        window_days=window_days,
        allowed=allowed,
        already_done=already_done,
    )


def _load_order(session: Session, order_id: str):
    repo = ShopOrderRepository(session)
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise NotFoundError("order not found") from None
    order = repo.get_by_id(order_uuid)
    if order is None:
        raise NotFoundError("order not found")
    return repo, order


def _policies_for(session: Session, order) -> list[dict]:
    """Per-line policy flags for an order (missing product → all False)."""
    repo = ProductRepository(session)
    lines = ShopOrderRepository(session).list_items(order.id)
    out = []
    for line in lines:
        policy = repo.get_policy(line.product_id)
        out.append(
            {
                "return_allowed": bool(policy and policy.return_allowed),
                "return_window_days": policy.return_window_days if policy else 0,
                "refund_allowed": bool(policy and policy.refund_allowed),
                "replacement_allowed": bool(policy and policy.replacement_allowed),
                "replacement_window_days": (
                    policy.replacement_window_days if policy else 0
                ),
                "cancellation_allowed": bool(policy and policy.cancellation_allowed),
            }
        )
    return out


def _prior_actions(session: Session, order_id) -> list[ShopAction]:
    return list(
        session.scalars(
            select(ShopAction).where(ShopAction.order_id == order_id)
        ).all()
    )


def _refunded_total(actions: list[ShopAction]) -> int:
    return sum(a.amount_paise or 0 for a in actions if a.action_type == ACTION_REFUND)


def _has_action(actions: list[ShopAction], action_type: str) -> bool:
    return any(a.action_type == action_type for a in actions)


def eligibility(session: Session, *, action_type: str, order_id: str) -> dict:
    """Eligibility report for one action against one order."""
    if action_type not in ACTION_TYPES:
        raise UnprocessableError(f"unknown action (use one of: {', '.join(ACTION_TYPES)})")
    _, order = _load_order(session, order_id)
    policies = _policies_for(session, order)
    actions = _prior_actions(session, order.id)
    now = datetime.datetime.now(datetime.UTC)

    if action_type == ACTION_CANCEL:
        cancellable = bool(policies) and all(p["cancellation_allowed"] for p in policies)
        return check_cancellation(
            status=order.status,
            cancellable=cancellable,
            has_cancel_action=_has_action(actions, ACTION_CANCEL),
        )
    if action_type == ACTION_REFUND:
        allowed = bool(policies) and all(p["refund_allowed"] for p in policies)
        return check_refund(
            payment_status=order.payment_status,
            refund_allowed=allowed,
            total_paise=order.total_paise,
            already_refunded_paise=_refunded_total(actions),
        )
    if action_type == ACTION_RETURN:
        allowed = bool(policies) and all(p["return_allowed"] for p in policies)
        window = min([p["return_window_days"] for p in policies], default=0)
        delivered = order.delivered_at or (
            now
            if order.status == ORDER_DELIVERED
            or resolve_status(
                order.ordered_at, now,
                delay_seconds=get_settings().delivery_delay_seconds,
            )
            == ORDER_DELIVERED
            else None
        )
        return check_return(
            delivered_at=delivered,
            now=now,
            window_days=window,
            allowed=allowed,
            already_done=_has_action(actions, ACTION_RETURN),
        )
    allowed = bool(policies) and all(p["replacement_allowed"] for p in policies)
    window = min([p["replacement_window_days"] for p in policies], default=0)
    delivered = order.delivered_at or (
        now
        if order.status == ORDER_DELIVERED
        or resolve_status(
            order.ordered_at, now,
            delay_seconds=get_settings().delivery_delay_seconds,
        )
        == ORDER_DELIVERED
        else None
    )
    return check_replacement(
        delivered_at=delivered,
        now=now,
        window_days=window,
        allowed=allowed,
        already_done=_has_action(actions, ACTION_REPLACE),
    )


def _serialize_action(row: ShopAction, order_number: str) -> dict:
    return {
        "id": str(row.id),
        "action_type": row.action_type,
        "order_id": str(row.order_id),
        "order_number": order_number,
        "ticket_id": str(row.ticket_id) if row.ticket_id else None,
        "amount_paise": row.amount_paise,
        "status": row.status,
        "mutation_key": row.mutation_key,
        "created_at": row.created_at.isoformat(),
    }


def execute_action(
    session: Session,
    *,
    action_type: str,
    order_id: str,
    ticket_id: str | None,
    mutation_key: str,
    amount_paise: int | None = None,
) -> dict:
    """Execute a mock action (idempotent by mutation key, single commit)."""
    if action_type not in ACTION_TYPES:
        raise UnprocessableError(f"unknown action (use one of: {', '.join(ACTION_TYPES)})")
    key = mutation_key.strip()
    if not key:
        raise UnprocessableError("mutation_key is required")
    existing = session.scalars(
        select(ShopAction).where(ShopAction.mutation_key == key)
    ).first()
    if existing is not None:
        raise ConflictError("mutation_key already used")

    _, order = _load_order(session, order_id)
    if order.status in ORDER_TERMINAL:
        raise UnprocessableError(f"order is {order.status}, no actions allowed")
    report = eligibility(session, action_type=action_type, order_id=order_id)
    if not report["eligible"]:
        raise UnprocessableError(f"action not eligible: {'; '.join(report['reasons'])}")

    ticket_uuid = None
    if ticket_id is not None:
        ticket_repo = CustomerTicketRepository(session)
        try:
            ticket_uuid = uuid.UUID(ticket_id)
        except ValueError:
            raise NotFoundError("ticket not found") from None
        if ticket_repo.get_by_id(ticket_uuid) is None:
            raise NotFoundError("ticket not found")

    amount = None
    if action_type == ACTION_REFUND:
        amount = amount_paise if amount_paise else order.total_paise
        if amount <= 0 or amount > order.total_paise:
            raise UnprocessableError("refund amount out of range")
    if action_type == ACTION_CANCEL:
        order.status = ORDER_CANCELLED
    elif action_type == ACTION_RETURN:
        order.status = ORDER_RETURNED

    row = ShopAction(
        ticket_id=ticket_uuid,
        order_id=order.id,
        action_type=action_type,
        amount_paise=amount,
        status=ACTION_DONE,
        mutation_key=key,
    )
    session.add(row)
    session.flush()
    if ticket_uuid is not None:
        CustomerTicketRepository(session).add_message(
            ticket_id=ticket_uuid,
            sender_type=SENDER_SYSTEM,
            sender_id=None,
            message=f"Mock {action_type.lower()} executed for order {order.order_number}.",
        )
    session.commit()
    session.refresh(row)
    return _serialize_action(row, order.order_number)


def get_action(session: Session, *, action_id: str) -> dict:
    """Re-read one action by id (execute → verify)."""
    try:
        row = session.get(ShopAction, uuid.UUID(action_id))
    except ValueError:
        raise NotFoundError("action not found") from None
    if row is None:
        raise NotFoundError("action not found")
    _, order = _load_order(session, str(row.order_id))
    return _serialize_action(row, order.order_number)


def get_action_by_key(session: Session, *, mutation_key: str) -> dict:
    """Re-read one action by mutation key (retry-safe verification)."""
    row = session.scalars(
        select(ShopAction).where(ShopAction.mutation_key == mutation_key.strip())
    ).first()
    if row is None:
        raise NotFoundError("action not found")
    _, order = _load_order(session, str(row.order_id))
    return _serialize_action(row, order.order_number)
