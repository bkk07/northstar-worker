"""`biz.shop_orders` + lines + mock payments data access (no business logic)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.biz.shop_order import ShopOrder, ShopOrderItem, ShopPayment


class ShopOrderRepository:
    """Thin queries over Phase 4 checkout orders."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def create_order(
        self,
        *,
        user_id: uuid.UUID | str,
        order_number: str,
        subtotal_paise: int,
        shipping_address: str,
        estimated_delivery,
    ) -> ShopOrder:
        row = ShopOrder(
            user_id=user_id,
            order_number=order_number,
            status="PROCESSING",
            subtotal_paise=subtotal_paise,
            total_paise=subtotal_paise,
            payment_status="SUCCESS",
            shipping_address=shipping_address,
            estimated_delivery=estimated_delivery,
        )
        self._s.add(row)
        self._s.flush()
        return row

    def add_item(
        self,
        *,
        order_id,
        product_id,
        product_name_snapshot: str,
        quantity: int,
        unit_price_paise: int,
    ) -> ShopOrderItem:
        row = ShopOrderItem(
            order_id=order_id,
            product_id=product_id,
            product_name_snapshot=product_name_snapshot,
            quantity=quantity,
            unit_price_paise=unit_price_paise,
        )
        self._s.add(row)
        self._s.flush()
        return row

    def create_payment(self, *, order_id, payment_reference: str, amount_paise: int) -> ShopPayment:
        row = ShopPayment(
            order_id=order_id,
            payment_reference=payment_reference,
            amount_paise=amount_paise,
            status="SUCCESS",
            method="MOCK",
        )
        self._s.add(row)
        self._s.flush()
        return row

    def list_by_user(self, user_id: uuid.UUID | str) -> list[ShopOrder]:
        return list(
            self._s.scalars(
                select(ShopOrder)
                .where(ShopOrder.user_id == user_id)
                .order_by(ShopOrder.ordered_at.desc())
            ).all()
        )

    def get_by_id(self, order_id: uuid.UUID | str) -> ShopOrder | None:
        return self._s.get(ShopOrder, order_id)

    def list_items(self, order_id: uuid.UUID | str) -> list[ShopOrderItem]:
        return list(
            self._s.scalars(
                select(ShopOrderItem).where(ShopOrderItem.order_id == order_id)
            ).all()
        )

    def get_payment(self, order_id: uuid.UUID | str) -> ShopPayment | None:
        return self._s.scalars(
            select(ShopPayment).where(ShopPayment.order_id == order_id)
        ).first()
