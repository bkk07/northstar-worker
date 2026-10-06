"""Phase 4 checkout + mock-payment + lifecycle service.

Mock automation without infra (spec §10): order status advances lazily from
`ordered_at` against `delivery_delay_seconds` — PROCESSING for the first
half, SHIPPED for the second, DELIVERED after. Reads persist advancement so
the support console (Phase 6) sees the same status. `resolve_status` and
`build_timeline` are pure (unit-testable).
"""

import datetime
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
from app.repositories.orders.order_repository import ShopOrderRepository
from app.repositories.products.cart_repository import CartRepository
from app.repositories.products.product_repository import ProductRepository
from app.services.products import product_service
from database.models.biz.product import CART_ORDERED
from database.models.biz.shop_order import ORDER_DELIVERED, ORDER_PROCESSING, ORDER_SHIPPED


def generate_order_number() -> str:
    """Human order number (`ORD-XXXXXX`, unique-guarded by DB)."""
    return f"ORD-{uuid.uuid4().hex[:6].upper()}"


def generate_payment_reference() -> str:
    """Mock payment reference (`PAY-XXXXXXXX`)."""
    return f"PAY-{uuid.uuid4().hex[:8].upper()}"


def resolve_status(
    ordered_at: datetime.datetime, now: datetime.datetime, *, delay_seconds: int
) -> str:
    """Lifecycle stage from elapsed time (pure)."""
    elapsed = (now - ordered_at).total_seconds()
    if elapsed >= delay_seconds:
        return ORDER_DELIVERED
    if elapsed >= delay_seconds / 2:
        return ORDER_SHIPPED
    return ORDER_PROCESSING


def build_timeline(
    status: str, *, ordered_at: str, paid_at: str, delivered_at: str | None
) -> list[dict]:
    """Five UI steps (spec §10) with done flags (pure)."""
    stage = {
        ORDER_PROCESSING: 2,
        ORDER_SHIPPED: 3,
        ORDER_DELIVERED: 4,
    }.get(status, 2)
    steps = [
        ("placed", "Order placed", ordered_at),
        ("payment", "Payment confirmed", paid_at),
        ("processing", "Processing", ordered_at if stage >= 2 else None),
        ("shipped", "Shipped", None),
        ("delivered", "Delivered", delivered_at),
    ]
    return [
        {"key": key, "label": label, "done": i <= stage, "at": at}
        for i, (key, label, at) in enumerate(steps)
    ]


def _iso(value: datetime.datetime | None) -> str | None:
    return value.isoformat() if value else None


def _serialize_detail(
    order, items: list[dict], payment: dict, *, delay_seconds: int, now: datetime.datetime
) -> dict:
    status = resolve_status(order.ordered_at, now, delay_seconds=delay_seconds)
    ordered_iso = order.ordered_at.isoformat()
    paid_iso = payment["paid_at"]
    delivered_iso = _iso(order.delivered_at) or (
        now.isoformat() if status == ORDER_DELIVERED else None
    )
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "status": status,
        "subtotal_paise": order.subtotal_paise,
        "total_paise": order.total_paise,
        "total_display": product_service.format_price(order.total_paise),
        "payment_status": order.payment_status,
        "item_count": len(items),
        "ordered_at": ordered_iso,
        "estimated_delivery": order.estimated_delivery.isoformat(),
        "shipping_address": order.shipping_address,
        "delivered_at": delivered_iso,
        "items": items,
        "payment": payment,
        "timeline": build_timeline(
            status, ordered_at=ordered_iso, paid_at=paid_iso, delivered_at=delivered_iso
        ),
    }


def _advance(session: Session, order, *, delay_seconds: int, now: datetime.datetime) -> str:
    """Persist lifecycle advancement so reads converge on the true stage."""
    status = resolve_status(order.ordered_at, now, delay_seconds=delay_seconds)
    if status != order.status:
        order.status = status
        if status == ORDER_DELIVERED and order.delivered_at is None:
            order.delivered_at = now
        session.commit()
        session.refresh(order)
    return status


def checkout(
    session: Session,
    *,
    user_id: str,
    shipping_address: str,
    delay_seconds: int,
    now: datetime.datetime | None = None,
) -> dict:
    """Cart → mock SUCCESS payment → PROCESSING order (single commit)."""
    address = shipping_address.strip()
    if len(address) < 10:
        raise UnprocessableError("shipping address is too short")
    cart_repo = CartRepository(session)
    cart = cart_repo.get_open_cart(user_id)
    if cart is None:
        raise UnprocessableError("cart is empty")
    lines = cart_repo.list_items(cart.id)
    if not lines:
        raise UnprocessableError("cart is empty")

    prod_repo = ProductRepository(session)
    subtotal = 0
    snapshots = []
    for line in lines:
        product = prod_repo.get_by_id(line.product_id)
        if product is None or not product.is_active:
            raise UnprocessableError("a cart product is no longer available")
        if line.quantity > product.stock:
            raise UnprocessableError(f"not enough stock for {product.name}")
        subtotal += line.quantity * line.unit_price_paise
        snapshots.append((line, product))
    if subtotal <= 0:
        raise UnprocessableError("cart total must be positive")

    placed = now or datetime.datetime.now(datetime.UTC)
    estimated = placed + datetime.timedelta(seconds=delay_seconds)
    repo = ShopOrderRepository(session)
    order = repo.create_order(
        user_id=user_id,
        order_number=generate_order_number(),
        subtotal_paise=subtotal,
        shipping_address=address,
        estimated_delivery=estimated,
    )
    order.ordered_at = placed
    items = []
    for line, product in snapshots:
        product.stock -= line.quantity
        repo.add_item(
            order_id=order.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            quantity=line.quantity,
            unit_price_paise=line.unit_price_paise,
        )
        items.append(
            {
                "id": str(line.id),
                "product_id": str(product.id),
                "product_name": product.name,
                "quantity": line.quantity,
                "unit_price_paise": line.unit_price_paise,
                "line_total_paise": line.quantity * line.unit_price_paise,
            }
        )
    payment_row = repo.create_payment(
        order_id=order.id,
        payment_reference=generate_payment_reference(),
        amount_paise=subtotal,
    )
    payment_row.paid_at = placed
    cart.status = CART_ORDERED
    session.commit()
    session.refresh(order)

    payment = {
        "payment_reference": payment_row.payment_reference,
        "amount_paise": payment_row.amount_paise,
        "amount_display": product_service.format_price(payment_row.amount_paise),
        "status": payment_row.status,
        "method": payment_row.method,
        "paid_at": placed.isoformat(),
    }
    return _serialize_detail(order, items, payment, delay_seconds=delay_seconds, now=placed)


def list_orders(
    session: Session, *, user_id: str, delay_seconds: int, now: datetime.datetime | None = None
) -> list[dict]:
    """Own orders, newest first, with live lifecycle status."""
    moment = now or datetime.datetime.now(datetime.UTC)
    repo = ShopOrderRepository(session)
    out = []
    for order in repo.list_by_user(user_id):
        status = _advance(session, order, delay_seconds=delay_seconds, now=moment)
        count = len(repo.list_items(order.id))
        out.append(
            {
                "id": str(order.id),
                "order_number": order.order_number,
                "status": status,
                "subtotal_paise": order.subtotal_paise,
                "total_paise": order.total_paise,
                "total_display": product_service.format_price(order.total_paise),
                "payment_status": order.payment_status,
                "item_count": count,
                "ordered_at": order.ordered_at.isoformat(),
                "estimated_delivery": order.estimated_delivery.isoformat(),
            }
        )
    return out


def get_order(
    session: Session,
    *,
    user_id: str,
    order_id: str,
    delay_seconds: int,
    now: datetime.datetime | None = None,
) -> dict:
    """Order tracking detail (ownership-checked)."""
    repo = ShopOrderRepository(session)
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise NotFoundError("order not found") from None
    order = repo.get_by_id(order_uuid)
    if order is None:
        raise NotFoundError("order not found")
    if str(order.user_id) != str(user_id):
        raise ForbiddenError("order belongs to another customer")
    moment = now or datetime.datetime.now(datetime.UTC)
    _advance(session, order, delay_seconds=delay_seconds, now=moment)
    items = [
        {
            "id": str(line.id),
            "product_id": str(line.product_id),
            "product_name": line.product_name_snapshot,
            "quantity": line.quantity,
            "unit_price_paise": line.unit_price_paise,
            "line_total_paise": line.quantity * line.unit_price_paise,
        }
        for line in repo.list_items(order.id)
    ]
    payment_row = repo.get_payment(order.id)
    if payment_row is None:
        raise NotFoundError("order payment not found")
    payment = {
        "payment_reference": payment_row.payment_reference,
        "amount_paise": payment_row.amount_paise,
        "amount_display": product_service.format_price(payment_row.amount_paise),
        "status": payment_row.status,
        "method": payment_row.method,
        "paid_at": payment_row.paid_at.isoformat(),
    }
    return _serialize_detail(order, items, payment, delay_seconds=delay_seconds, now=moment)
