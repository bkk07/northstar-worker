"""Eligibility: is the customer entitled? (E-* rules, plan §16).

Entitlement is a property of the world (delivery, window, prior state),
not of the worker's authority. Returns the failing rule with a reason,
or None when entitled. Pure functions of facts — no tools, no LLM.
"""

import datetime

from agent.policy import rules
from agent.policy.facts import Facts


def check_replacement(
    facts: Facts, order_item_id: str, today: datetime.date
) -> tuple[str, str] | None:
    """E-REPL-001: damage reported, delivered, in window, not replaced."""
    order = facts.order
    ticket = facts.ticket
    if not order or not ticket:
        return ("P-FAIL-CLOSED", "replacement needs order and ticket facts")
    if not _damage_reported(ticket):
        return ("E-REPL-001", "no damage reported on the ticket")
    if order.get("status") != "delivered":
        return ("E-REPL-001", f"order status is {order.get('status')!r}, not delivered")
    window = facts.threshold("E-REPL-001", "window_days", rules.REPL_WINDOW_DAYS)
    delivered = _delivered_date(order)
    if delivered is None:
        return ("P-FAIL-CLOSED", "order has no delivery date")
    if (today - delivered).days > window:
        return ("E-REPL-001", f"delivered {(today - delivered).days} days ago (window {window})")
    if facts.existing_replacement:
        return ("E-REPL-001", "item already has an active replacement")
    if not _item_in_order(order, order_item_id):
        return ("E-REPL-001", "item is not on the order")
    return None


def check_refund(facts: Facts, amount_paise: int) -> tuple[str, str] | None:
    """E-REF-001 (amount ≤ paid) and E-REF-002 (refundable category)."""
    order = facts.order
    if not order:
        return ("P-FAIL-CLOSED", "refund needs order facts")
    paid = order.get("paid_paise")
    if paid is None:
        return ("P-FAIL-CLOSED", "order has no paid amount")
    if amount_paise > paid:
        return ("E-REF-001", f"refund {amount_paise} exceeds paid {paid}")
    non_refundable = set(
        facts.threshold(
            "E-REF-002", "non_refundable_categories", sorted(rules.NON_REFUNDABLE_CATEGORIES)
        )
    )
    items = order.get("items", [])
    bad = sorted({item.get("category", "") for item in items} & non_refundable)
    if bad:
        return ("E-REF-002", f"non-refundable categories: {', '.join(bad)}")
    return None


def _damage_reported(ticket: dict) -> bool:
    if ticket.get("category", "") in rules.DAMAGE_CATEGORIES:
        return True
    text = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    return any(hint in text for hint in rules.DAMAGE_HINTS)


def _delivered_date(order: dict) -> datetime.date | None:
    raw = order.get("delivered_at")
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(str(raw)).date()
    except ValueError:
        return None


def _item_in_order(order: dict, order_item_id: str) -> bool:
    return any(item.get("id") == order_item_id for item in order.get("items", []))
