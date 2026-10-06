"""Phase 3 cart service: open cart per user, snapshot prices, totals.

`cart_totals` is pure (unit-testable); the service owns stock checks and
ownership checks.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
from app.repositories.products.cart_repository import CartRepository
from app.repositories.products.product_repository import ProductRepository


def cart_totals(items: list[dict]) -> dict:
    """Subtotal/total from line DTOs (pure, unit-testable)."""
    subtotal = sum(i["quantity"] * i["unit_price_paise"] for i in items)
    return {"subtotal_paise": subtotal, "total_paise": subtotal, "item_count": len(items)}


def _serialize_cart(repo: CartRepository, prod_repo: ProductRepository, cart) -> dict:
    """Cart + lines → DTO with product names and totals."""
    lines = []
    for line in repo.list_items(cart.id):
        product = prod_repo.get_by_id(line.product_id)
        lines.append(
            {
                "id": str(line.id),
                "product_id": str(line.product_id),
                "product_name": product.name if product else "Unknown product",
                "quantity": line.quantity,
                "unit_price_paise": line.unit_price_paise,
                "line_total_paise": line.quantity * line.unit_price_paise,
            }
        )
    totals = cart_totals(lines)
    return {"id": str(cart.id), "items": lines, **totals}


def get_cart(session: Session, *, user_id: str) -> dict:
    """Active cart (empty shell when the user never added anything)."""
    repo = CartRepository(session)
    cart = repo.get_open_cart(user_id)
    if cart is None:
        return {"id": "", "items": [], "subtotal_paise": 0, "total_paise": 0, "item_count": 0}
    return _serialize_cart(repo, ProductRepository(session), cart)


def add_item(session: Session, *, user_id: str, product_id: str, quantity: int) -> dict:
    """Add a product (or bump quantity), snapshotting the current price."""
    prod_repo = ProductRepository(session)
    product = prod_repo.get_by_id(product_id)
    if product is None or not product.is_active:
        raise NotFoundError("product not found")
    if product.stock <= 0:
        raise UnprocessableError("product out of stock")
    repo = CartRepository(session)
    cart = repo.get_open_cart(user_id) or repo.create_cart(user_id)
    existing = repo.find_item(cart.id, product.id)
    new_qty = quantity + (existing.quantity if existing else 0)
    if new_qty > product.stock:
        raise UnprocessableError("not enough stock")
    if existing:
        existing.quantity = new_qty
    else:
        repo.add_item(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            unit_price_paise=product.price_paise,
        )
    session.commit()
    session.refresh(cart)
    return _serialize_cart(repo, prod_repo, cart)


def update_item(session: Session, *, user_id: str, item_id: str, quantity: int) -> dict:
    """Set a line quantity (ownership-checked)."""
    repo = CartRepository(session)
    line = repo.get_item(item_id)
    if line is None:
        raise NotFoundError("cart item not found")
    cart = repo.get_open_cart(user_id)
    if cart is None or str(line.cart_id) != str(cart.id):
        raise ForbiddenError("cart item belongs to another cart")
    product = ProductRepository(session).get_by_id(line.product_id)
    if product and quantity > product.stock:
        raise UnprocessableError("not enough stock")
    line.quantity = quantity
    session.commit()
    session.refresh(cart)
    return _serialize_cart(repo, ProductRepository(session), cart)


def remove_item(session: Session, *, user_id: str, item_id: str) -> dict:
    """Remove a line (ownership-checked)."""
    repo = CartRepository(session)
    line = repo.get_item(item_id)
    if line is None:
        raise NotFoundError("cart item not found")
    cart = repo.get_open_cart(user_id)
    if cart is None or str(line.cart_id) != str(cart.id):
        raise ForbiddenError("cart item belongs to another cart")
    repo.delete_item(line)
    session.commit()
    session.refresh(cart)
    return _serialize_cart(repo, ProductRepository(session), cart)
