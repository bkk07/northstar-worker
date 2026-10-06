"""Phase 5 customer-ticket unit tests (no DB, no docker).

Covers: ticket-number format, category/priority normalization, and
raise-ticket/message DTO validation.
"""

import pytest
from pydantic import ValidationError

from app.core.exceptions import UnprocessableError
from app.schemas.tickets import TicketCreate, TicketDetail, TicketMessageCreate
from app.services.tickets import ticket_service


def test_ticket_number_format() -> None:
    number = ticket_service.generate_ticket_number()
    assert number.startswith("TKT-") and len(number) == 10
    assert ticket_service.generate_ticket_number() != ticket_service.generate_ticket_number()


def test_normalize_category() -> None:
    assert ticket_service.normalize_category("refund") == "REFUND"
    assert ticket_service.normalize_category("  General ") == "GENERAL"
    with pytest.raises(UnprocessableError):
        ticket_service.normalize_category("WARRANTY")


def test_normalize_priority() -> None:
    assert ticket_service.normalize_priority("high") == "HIGH"
    assert ticket_service.normalize_priority("NORMAL") == "NORMAL"
    with pytest.raises(UnprocessableError):
        ticket_service.normalize_priority("ASAP")


def test_ticket_create_dto_validation() -> None:
    with pytest.raises(ValidationError):
        TicketCreate(subject="Hi", category="REFUND", description="Long enough description here")
    with pytest.raises(ValidationError):
        TicketCreate(subject="Damaged item", category="REFUND", description="short")
    ok = TicketCreate(
        subject="Damaged item",
        category="REFUND",
        description="The screen arrived cracked, please help.",
        order_id="o1",
    )
    assert ok.priority == "NORMAL"
    assert ok.order_id == "o1"


def test_ticket_message_dto_validation() -> None:
    with pytest.raises(ValidationError):
        TicketMessageCreate(message="")
    ok = TicketMessageCreate(message="Any update on this?")
    assert ok.message.startswith("Any")


def test_ticket_detail_dto_shape() -> None:
    detail = TicketDetail(
        id="t1",
        ticket_number="TKT-ABC123",
        subject="Damaged item",
        description="The screen arrived cracked.",
        category="REFUND",
        priority="HIGH",
        status="OPEN",
        resolution=None,
        created_at="2026-01-01T00:00:00+00:00",
        related_order={
            "id": "o1",
            "order_number": "ORD-ABC123",
            "status": "DELIVERED",
            "total_display": "₹1,299",
            "item_count": 1,
        },
        messages=[
            {
                "id": "m1",
                "sender_type": "CUSTOMER",
                "message": "The screen arrived cracked.",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )
    assert detail.status == "OPEN"
    assert detail.related_order is not None
    assert detail.related_order.order_number == "ORD-ABC123"
