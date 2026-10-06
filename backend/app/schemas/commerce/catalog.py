"""Catalog DTOs: dummy product catalog + per-product policies (read-only)."""

from typing import Any

from pydantic import BaseModel


class PolicyRead(BaseModel):
    """One policy rule with a human-readable summary for the console."""

    rule_key: str
    summary: str
    params: dict[str, Any]
    version: int


class ProductRead(BaseModel):
    """One catalog product (distinct SKU across seeded order items)."""

    sku: str
    title: str
    category: str
    unit_paise: int
    orders_count: int


class ProductDetailRead(BaseModel):
    """Product plus the policies that apply to it."""

    product: ProductRead
    policies: list[PolicyRead]
