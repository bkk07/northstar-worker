"""Snapshot scope readers: plain-data reads of the contract's entities.

The verifier owns its reads: scoped collections plus whole-table counts
(the counts catch writes outside the scope). Input is a SQLAlchemy
session from the caller; this module imports only `database.models`
(never `agent` or `backend`), per the independence contract.
"""

from typing import Any

from sqlalchemy.orm import Session

from database.models.biz.customer import Customer
from database.models.biz.financial import Refund, Replacement
from database.models.biz.order import Order, OrderItem
from database.models.biz.ticket import Ticket, TicketNote

COLLECTIONS = (
    "customers",
    "orders",
    "order_items",
    "tickets",
    "ticket_notes",
    "refunds",
    "replacements",
)


def _ids(values: object) -> list[Any]:
    """Scope id lists as given (UUIDs or strings); empty when missing."""
    if not isinstance(values, list):
        return []
    return list(values)


def read_scope(session: Session, scope: dict[str, Any]) -> dict[str, Any]:
    """Read every row the contract may touch, plus per-table counts."""
    customer_ids = _ids(scope.get("customer_ids"))
    order_ids = _ids(scope.get("order_ids"))
    ticket_ids = _ids(scope.get("ticket_ids"))

    orders = (
        session.query(Order)
        .filter((Order.id.in_(order_ids)) | (Order.customer_id.in_(customer_ids)))
        .all()
        if (order_ids or customer_ids)
        else []
    )
    order_row_ids = [row.id for row in orders]
    tickets = (
        session.query(Ticket)
        .filter((Ticket.id.in_(ticket_ids)) | (Ticket.order_id.in_(order_row_ids)))
        .all()
        if (ticket_ids or order_row_ids)
        else []
    )
    ticket_row_ids = [row.id for row in tickets]

    data = {
        "customers": [
            _row(row) for row in session.query(Customer).filter(Customer.id.in_(customer_ids)).all()
        ]
        if customer_ids
        else [],
        "orders": [_row(row) for row in orders],
        "order_items": [
            _row(row)
            for row in session.query(OrderItem).filter(OrderItem.order_id.in_(order_row_ids)).all()
        ]
        if order_row_ids
        else [],
        "tickets": [_row(row) for row in tickets],
        "ticket_notes": [
            _row(row)
            for row in session.query(TicketNote)
            .filter(TicketNote.ticket_id.in_(ticket_row_ids))
            .all()
        ]
        if ticket_row_ids
        else [],
        "refunds": [
            _row(row)
            for row in session.query(Refund)
            .filter((Refund.order_id.in_(order_row_ids)) | (Refund.ticket_id.in_(ticket_row_ids)))
            .all()
        ]
        if (order_row_ids or ticket_row_ids)
        else [],
        "replacements": [
            _row(row)
            for row in session.query(Replacement)
            .filter(
                (Replacement.order_id.in_(order_row_ids))
                | (Replacement.ticket_id.in_(ticket_row_ids))
            )
            .all()
        ]
        if (order_row_ids or ticket_row_ids)
        else [],
        "counts": {
            "customers": session.query(Customer).count(),
            "orders": session.query(Order).count(),
            "order_items": session.query(OrderItem).count(),
            "tickets": session.query(Ticket).count(),
            "ticket_notes": session.query(TicketNote).count(),
            "refunds": session.query(Refund).count(),
            "replacements": session.query(Replacement).count(),
        },
    }
    return data


def _row(row: Any) -> dict[str, Any]:
    """One ORM row as plain data (UUIDs and datetimes canonicalized)."""
    out = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        out[column.name] = _scalar(value)
    return out


def _scalar(value: object) -> Any:
    """Canonical scalar: UUID and datetime objects become strings."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
