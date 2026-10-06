"""PRODUCT tools: support-plane reads over the Phase 3 catalog (spec Phase 7)."""

from app.repositories.products.product_repository import ProductRepository
from app.services.products import product_service
from mcp_server.support import db
from mcp_server.support.envelopes import fail, ok, require_text, run_guarded


def get_product(product_id: str) -> dict:
    """Product card data by id."""
    def _call():
        pid = require_text(product_id, "product_id", maximum=64)
        with db.support_session() as session:
            product = ProductRepository(session).get_by_id(pid)
            if product is None or not product.is_active:
                return fail("product not found", code="NOT_FOUND")
            return ok(product=product_service.to_list_item(product))

    return run_guarded(_call)


def get_product_details(product_id: str) -> dict:
    """Full product detail with policy summary."""
    def _call():
        pid = require_text(product_id, "product_id", maximum=64)
        with db.support_session() as session:
            return ok(product=product_service.get_product(session, product_id=pid))

    return run_guarded(_call)


def get_product_policy(product_id: str) -> dict:
    """Every policy flag for one product, plus the one-line summary."""
    def _call():
        pid = require_text(product_id, "product_id", maximum=64)
        with db.support_session() as session:
            repo = ProductRepository(session)
            product = repo.get_by_id(pid)
            if product is None:
                return fail("product not found", code="NOT_FOUND")
            summary = product_service.summarize_policy(repo.get_policy(product.id))
            return ok(product_name=product.name, policy=summary)

    return run_guarded(_call)
