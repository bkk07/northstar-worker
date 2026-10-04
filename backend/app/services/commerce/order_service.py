"""Order read service."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.commerce.order_repository import OrderRepository
from app.schemas.commerce.order import OrderItemRead, OrderRead
from database.models.biz.order import Order, OrderItem


class OrderService:
    """Order queries with items attached."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repos = OrderRepository(session)

    def get_by_id(self, order_id: uuid.UUID) -> OrderRead:
        """One order with items or 404."""
        order = self._repos.get_by_id(Order, order_id)
        if order is None:
            raise NotFoundError(f"order {order_id} not found")
        return self._to_dto(order, self._repos.list_items(order.id))

    def get_by_code(self, code: str) -> OrderRead:
        """One order with items by human code or 404."""
        order = self._repos.get_by_code(code)
        if order is None:
            raise NotFoundError(f"order {code} not found")
        return self._to_dto(order, self._repos.list_items(order.id))

    def list_by_customer(self, customer_id: uuid.UUID) -> list[OrderRead]:
        """Orders of one customer (items attached)."""
        result = []
        for order in self._repos.list_by_customer(customer_id):
            result.append(self._to_dto(order, self._repos.list_items(order.id)))
        return result

    @staticmethod
    def _to_dto(order: Order, items: list[OrderItem]) -> OrderRead:
        return OrderRead(
            id=order.id,
            code=order.code,
            customer_id=order.customer_id,
            status=order.status,
            total_paise=order.total_paise,
            paid_paise=order.paid_paise,
            placed_at=order.placed_at,
            delivered_at=order.delivered_at,
            items=[
                OrderItemRead(
                    id=i.id,
                    sku=i.sku,
                    title=i.title,
                    qty=i.qty,
                    unit_paise=i.unit_paise,
                    category=i.category,
                )
                for i in items
            ],
        )
