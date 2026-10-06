"""`biz.carts` + `biz.cart_items` data access (no business logic)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.biz.product import CART_OPEN, Cart, CartItem


class CartRepository:
    """Thin queries over carts and their lines."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def get_open_cart(self, user_id: uuid.UUID | str) -> Cart | None:
        return self._s.scalars(
            select(Cart).where(Cart.user_id == user_id, Cart.status == CART_OPEN)
        ).first()

    def create_cart(self, user_id: uuid.UUID | str) -> Cart:
        row = Cart(user_id=user_id, status=CART_OPEN)
        self._s.add(row)
        self._s.flush()
        return row

    def list_items(self, cart_id: uuid.UUID | str) -> list[CartItem]:
        return list(
            self._s.scalars(select(CartItem).where(CartItem.cart_id == cart_id)).all()
        )

    def get_item(self, item_id: uuid.UUID | str) -> CartItem | None:
        return self._s.get(CartItem, item_id)

    def find_item(self, cart_id: uuid.UUID | str, product_id: uuid.UUID | str) -> CartItem | None:
        return self._s.scalars(
            select(CartItem).where(
                CartItem.cart_id == cart_id, CartItem.product_id == product_id
            )
        ).first()

    def add_item(self, *, cart_id, product_id, quantity: int, unit_price_paise: int) -> CartItem:
        row = CartItem(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
            unit_price_paise=unit_price_paise,
        )
        self._s.add(row)
        self._s.flush()
        return row

    def delete_item(self, row: CartItem) -> None:
        self._s.delete(row)
