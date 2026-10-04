"""Policy test factories + DB migration fixture (no LLM, no backend)."""

import datetime

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session", autouse=True)
def _migrate_head():
    """Migrate to head once per session (tests use unique rows)."""
    command.upgrade(Config("database/alembic.ini"), "head")


TODAY = datetime.date(2026, 10, 4)


def order(days_ago=5, paid=8500000, status="delivered", items=None, customer="c-101"):
    """Delivered order fact with line items."""
    return {
        "id": "o-1942",
        "code": "ORD-1942",
        "customer_id": customer,
        "status": status,
        "total_paise": paid,
        "paid_paise": paid,
        "delivered_at": (TODAY - datetime.timedelta(days=days_ago)).isoformat(),
        "items": items
        if items is not None
        else [
            {
                "id": "i-1",
                "title": "ProBook",
                "sku": "LAP",
                "qty": 1,
                "unit_paise": paid,
                "category": "electronics",
            }
        ],
    }


def ticket(customer="c-101", order_id="o-1942", category="damage"):
    """Ticket fact (category damage reports damage by itself)."""
    return {
        "id": "t-101",
        "code": "TCK-101",
        "customer_id": customer,
        "order_id": order_id,
        "subject": "Cracked screen",
        "body": "Please replace it.",
        "category": category,
        "status": "open",
    }
