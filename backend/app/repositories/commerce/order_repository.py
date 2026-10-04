"""Order and item reads."""

import uuid

from app.repositories.base import BaseRepository
from database.models.biz.order import Order, OrderItem


class OrderRepository(BaseRepository[Order]):
    """Read access to `biz.orders` and `biz.order_items`."""

    def get_by_code(self, code: str) -> Order | None:
        """Fetch one order by human code."""
        return self._session.query(Order).filter(Order.code == code).one_or_none()

    def list_by_customer(self, customer_id: uuid.UUID) -> list[Order]:
        """All orders of one customer, newest placement first."""
        return (
            self._session.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.placed_at.desc())
            .all()
        )

    def list_items(self, order_id: uuid.UUID) -> list[OrderItem]:
        """Items of one order."""
        return (
            self._session.query(OrderItem)
            .filter(OrderItem.order_id == order_id)
            .order_by(OrderItem.sku)
            .all()
        )

    def get_item(self, order_id: uuid.UUID, sku: str) -> OrderItem | None:
        """One item of an order by SKU."""
        return (
            self._session.query(OrderItem)
            .filter(OrderItem.order_id == order_id, OrderItem.sku == sku)
            .one_or_none()
        )
