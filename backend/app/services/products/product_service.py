"""Phase 3 catalog service: products + per-product policy summaries.

Pure helpers (`format_price`, `summarize_policy`, `apply_filters`) are
unit-testable without a database.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.products.product_repository import ProductRepository
from database.models.biz.product import Product, ProductPolicy


def format_price(paise: int) -> str:
    """Format paise as `₹1,299`."""
    return f"₹{paise // 100:,}"


def summarize_policy(policy: ProductPolicy | None) -> dict:
    """One-line human summary plus flags for the product page."""
    if policy is None:
        return {
            "return_allowed": False,
            "return_window_days": 0,
            "refund_allowed": False,
            "replacement_allowed": False,
            "replacement_window_days": 0,
            "cancellation_allowed": False,
            "warranty_days": 0,
            "summary": "No policy on file — contact support.",
        }
    bits = []
    if policy.refund_allowed:
        bits.append("refundable")
    if policy.return_allowed:
        bits.append(f"{policy.return_window_days}-day returns")
    if policy.replacement_allowed:
        bits.append(f"{policy.replacement_window_days}-day replacement")
    if policy.cancellation_allowed:
        bits.append("cancellable")
    if policy.warranty_days:
        bits.append(f"{policy.warranty_days}-day warranty")
    return {
        "return_allowed": policy.return_allowed,
        "return_window_days": policy.return_window_days,
        "refund_allowed": policy.refund_allowed,
        "replacement_allowed": policy.replacement_allowed,
        "replacement_window_days": policy.replacement_window_days,
        "cancellation_allowed": policy.cancellation_allowed,
        "warranty_days": policy.warranty_days,
        "summary": "; ".join(bits).capitalize() if bits else "No returns or refunds.",
    }


def apply_filters(
    products: list[dict], *, q: str | None = None, category: str | None = None, sort: str = "name"
) -> list[dict]:
    """Search / filter / sort product DTOs (pure, unit-testable)."""
    rows = list(products)
    if q:
        needle = q.strip().lower()
        rows = [p for p in rows if needle in p["name"].lower() or needle in p["brand"].lower()]
    if category:
        rows = [p for p in rows if p["category"].lower() == category.strip().lower()]
    if sort == "price_asc":
        rows.sort(key=lambda p: p["price_paise"])
    elif sort == "price_desc":
        rows.sort(key=lambda p: -p["price_paise"])
    else:
        rows.sort(key=lambda p: p["name"].lower())
    return rows


def to_list_item(product: Product) -> dict:
    """Product row → card DTO."""
    return {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "category": product.category,
        "brand": product.brand,
        "price_paise": product.price_paise,
        "price_display": format_price(product.price_paise),
        "image_url": product.image_url,
        "stock": product.stock,
        "in_stock": product.stock > 0,
    }


def list_products(
    session: Session, *, q: str | None = None, category: str | None = None, sort: str = "name"
) -> list[dict]:
    """Active products with search / category / sort applied."""
    repo = ProductRepository(session)
    items = [to_list_item(p) for p in repo.list_active()]
    return apply_filters(items, q=q, category=category, sort=sort or "name")


def get_product(session: Session, *, product_id: str) -> dict:
    """Product detail with policy summary, or 404."""
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if product is None or not product.is_active:
        raise NotFoundError("product not found")
    detail = to_list_item(product)
    detail["description"] = product.description
    detail["policy"] = summarize_policy(repo.get_policy(product.id))
    return detail


def list_categories(session: Session) -> list[str]:
    """Distinct active categories for the filter UI."""
    return ProductRepository(session).categories()
