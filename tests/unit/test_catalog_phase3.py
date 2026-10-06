"""Phase 3 storefront unit tests (no DB, no docker).

Covers: price formatting, policy summaries, catalog search/filter/sort,
cart totals, and DTO validation.
"""

import pytest
from pydantic import ValidationError

from app.schemas.products import CartItemCreate, ProductDetail
from app.services.products import cart_service, product_service


def test_format_price() -> None:
    assert product_service.format_price(499900) == "₹4,999"
    assert product_service.format_price(89900) == "₹899"


def test_summarize_policy_none() -> None:
    summary = product_service.summarize_policy(None)
    assert summary["refund_allowed"] is False
    assert "contact support" in summary["summary"]


def test_summarize_policy_full() -> None:
    class P:
        return_allowed = True
        return_window_days = 7
        refund_allowed = True
        replacement_allowed = True
        replacement_window_days = 7
        cancellation_allowed = False
        warranty_days = 365

    summary = product_service.summarize_policy(P())  # type: ignore[arg-type]
    assert "7-day returns" in summary["summary"]
    assert "warranty" in summary["summary"]


def test_apply_filters_search_sort() -> None:
    products = [
        {"name": "Aura Headphones", "brand": "Aura", "category": "Audio", "price_paise": 499900},
        {"name": "Volt Power Bank", "brand": "Volt", "category": "Accessories",
         "price_paise": 299900},
        {"name": "Terra Tee", "brand": "Terra", "category": "Apparel", "price_paise": 89900},
    ]
    assert len(product_service.apply_filters(products, q="aura")) == 1
    assert len(product_service.apply_filters(products, category="audio")) == 1
    cheapest = product_service.apply_filters(products, sort="price_asc")
    assert cheapest[0]["name"] == "Terra Tee"
    priciest = product_service.apply_filters(products, sort="price_desc")
    assert priciest[0]["name"] == "Aura Headphones"


def test_cart_totals() -> None:
    totals = cart_service.cart_totals(
        [
            {"quantity": 2, "unit_price_paise": 499900},
            {"quantity": 1, "unit_price_paise": 89900},
        ]
    )
    assert totals["subtotal_paise"] == 2 * 499900 + 89900
    assert totals["total_paise"] == totals["subtotal_paise"]
    assert totals["item_count"] == 2
    assert cart_service.cart_totals([])["subtotal_paise"] == 0


def test_cart_item_dto_validation() -> None:
    with pytest.raises(ValidationError):
        CartItemCreate(product_id="p1", quantity=0)
    ok = CartItemCreate(product_id="p1", quantity=2)
    assert ok.quantity == 2


def test_product_detail_dto_shape() -> None:
    detail = ProductDetail(
        id="p1",
        name="Aura",
        slug="aura",
        description="d",
        category="Audio",
        brand="Aura",
        price_paise=499900,
        price_display="₹4,999",
        image_url="",
        stock=5,
        in_stock=True,
        policy={
            "return_allowed": True,
            "return_window_days": 7,
            "refund_allowed": True,
            "replacement_allowed": True,
            "replacement_window_days": 7,
            "cancellation_allowed": True,
            "warranty_days": 365,
            "summary": "Refundable; 7-day returns",
        },
    )
    assert detail.in_stock is True
