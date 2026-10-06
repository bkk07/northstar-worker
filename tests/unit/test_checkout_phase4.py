"""Phase 4 checkout/lifecycle unit tests (no DB, no docker).

Covers: lifecycle stage resolution, timeline done-flags, order/payment
reference formats, and checkout/order DTO validation.
"""

import datetime

import pytest
from pydantic import ValidationError

from app.schemas.orders import CheckoutCreate, OrderDetail
from app.services.orders import order_service


def _t(seconds: int = 0) -> datetime.datetime:
    return datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC) + datetime.timedelta(
        seconds=seconds
    )


def test_resolve_status_lifecycle() -> None:
    placed = _t()
    assert order_service.resolve_status(placed, _t(10), delay_seconds=60) == "PROCESSING"
    assert order_service.resolve_status(placed, _t(29), delay_seconds=60) == "PROCESSING"
    assert order_service.resolve_status(placed, _t(30), delay_seconds=60) == "SHIPPED"
    assert order_service.resolve_status(placed, _t(59), delay_seconds=60) == "SHIPPED"
    assert order_service.resolve_status(placed, _t(60), delay_seconds=60) == "DELIVERED"
    assert order_service.resolve_status(placed, _t(3600), delay_seconds=60) == "DELIVERED"


def test_timeline_processing_marks_first_three_done() -> None:
    steps = order_service.build_timeline(
        "PROCESSING", ordered_at="o", paid_at="p", delivered_at=None
    )
    assert [s["label"] for s in steps] == [
        "Order placed",
        "Payment confirmed",
        "Processing",
        "Shipped",
        "Delivered",
    ]
    assert [s["done"] for s in steps] == [True, True, True, False, False]


def test_timeline_shipped_and_delivered() -> None:
    shipped = order_service.build_timeline(
        "SHIPPED", ordered_at="o", paid_at="p", delivered_at=None
    )
    assert [s["done"] for s in shipped] == [True, True, True, True, False]
    delivered = order_service.build_timeline(
        "DELIVERED", ordered_at="o", paid_at="p", delivered_at="d"
    )
    assert all(s["done"] for s in delivered)
    assert delivered[-1]["at"] == "d"


def test_reference_formats() -> None:
    number = order_service.generate_order_number()
    assert number.startswith("ORD-") and len(number) == 10
    ref = order_service.generate_payment_reference()
    assert ref.startswith("PAY-") and len(ref) == 12
    assert order_service.generate_order_number() != order_service.generate_order_number()


def test_checkout_dto_validation() -> None:
    with pytest.raises(ValidationError):
        CheckoutCreate(shipping_address="short")
    ok = CheckoutCreate(shipping_address="221B Baker Street, London NW1 6XE")
    assert ok.shipping_address.startswith("221B")


def test_order_detail_dto_shape() -> None:
    payment = {
        "payment_reference": "PAY-ABC12345",
        "amount_paise": 129900,
        "amount_display": "₹1,299",
        "status": "SUCCESS",
        "method": "MOCK",
        "paid_at": "2026-01-01T00:00:00+00:00",
    }
    detail = OrderDetail(
        id="o1",
        order_number="ORD-ABC123",
        status="PROCESSING",
        subtotal_paise=129900,
        total_paise=129900,
        total_display="₹1,299",
        payment_status="SUCCESS",
        item_count=1,
        ordered_at="2026-01-01T00:00:00+00:00",
        estimated_delivery="2026-01-01T00:01:00+00:00",
        shipping_address="221B Baker Street, London NW1 6XE",
        delivered_at=None,
        items=[
            {
                "id": "i1",
                "product_id": "p1",
                "product_name": "Aura",
                "quantity": 1,
                "unit_price_paise": 129900,
                "line_total_paise": 129900,
            }
        ],
        payment=payment,
        timeline=[
            {"key": "placed", "label": "Order placed", "done": True, "at": "o"},
            {"key": "payment", "label": "Payment confirmed", "done": True, "at": "p"},
            {"key": "processing", "label": "Processing", "done": True, "at": "o"},
            {"key": "shipped", "label": "Shipped", "done": False, "at": None},
            {"key": "delivered", "label": "Delivered", "done": False, "at": None},
        ],
    )
    assert detail.status == "PROCESSING"
    assert detail.timeline[0].done is True
