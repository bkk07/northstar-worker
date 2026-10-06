"""`biz.products` + `biz.product_policies` data access (no business logic)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.biz.product import Product, ProductPolicy


class ProductRepository:
    """Thin queries over the storefront catalog."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def list_active(self) -> list[Product]:
        return list(
            self._s.scalars(
                select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
            ).all()
        )

    def get_by_id(self, product_id: uuid.UUID | str) -> Product | None:
        return self._s.get(Product, product_id)

    def get_policy(self, product_id: uuid.UUID | str) -> ProductPolicy | None:
        return self._s.scalars(
            select(ProductPolicy).where(ProductPolicy.product_id == product_id)
        ).first()

    def categories(self) -> list[str]:
        rows = self._s.scalars(
            select(Product.category)
            .where(Product.is_active.is_(True))
            .distinct()
            .order_by(Product.category)
        ).all()
        return list(rows)
