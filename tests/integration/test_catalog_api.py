"""Catalog API contract tests: products + per-product policies (live DB)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.commerce.catalog_service import summarize_rule
from database.seeds import loader


@pytest.fixture(scope="module")
def client():
    """Seeded world + test client (module-scoped, read-mostly)."""
    loader.seed()
    return TestClient(create_app())


def test_list_products_has_seeded_skus(client):
    """Distinct SKUs across seeded orders (HP-01, LAP-X1, ...)."""
    body = client.get("/api/catalog/products").json()
    by_sku = {p["sku"]: p for p in body}
    assert {"HP-01", "LAP-X1", "TV-55"} <= set(by_sku)
    assert by_sku["HP-01"]["title"] == "Studio Headphones"
    assert by_sku["HP-01"]["orders_count"] >= 1


def test_product_detail_carries_policies(client):
    """Product detail quotes refund/replacement policies with summaries."""
    body = client.get("/api/catalog/products/HP-01").json()
    assert body["product"]["sku"] == "HP-01"
    keys = [p["rule_key"] for p in body["policies"]]
    assert "P-REF-001" in keys and "P-REPL-001" in keys
    ref = next(p for p in body["policies"] if p["rule_key"] == "P-REF-001")
    assert "₹" in ref["summary"] and ref["version"] == 1


def test_product_lookup_case_insensitive_and_404(client):
    """SKU lookup ignores case; unknown SKUs 404."""
    assert client.get("/api/catalog/products/hp-01").json()["product"]["sku"] == "HP-01"
    assert client.get("/api/catalog/products/NOPE-00").status_code == 404


def test_list_policies_has_summaries(client):
    """Every policy carries a human summary."""
    body = client.get("/api/catalog/policies").json()
    assert len(body) == 14
    assert all(p["summary"] for p in body)


def test_summarize_rule_formats_rupees():
    """Policy summaries render paise as rupees."""
    assert summarize_rule("P-REF-001", {"max_paise": 500000, "max_count_90d": 2}) == (
        "Auto-approve refunds up to ₹5,000 (max 2 per 90 days)"
    )
    assert "final_sale" in summarize_rule(
        "E-REF-002", {"non_refundable_categories": ["final_sale"]}
    )
