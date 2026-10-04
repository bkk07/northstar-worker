"""Customer reads (look-alike search included)."""

from sqlalchemy import func, or_

from app.repositories.base import BaseRepository
from database.models.biz.customer import Customer


class CustomerRepository(BaseRepository[Customer]):
    """Read access to `biz.customers`."""

    def get_by_code(self, code: str) -> Customer | None:
        """Fetch one customer by human code."""
        return self._session.query(Customer).filter(Customer.code == code).one_or_none()

    def search(self, query: str, limit: int = 20) -> list[Customer]:
        """Substring match ordered by trigram similarity (look-alikes first)."""
        pattern = f"%{query}%"
        return (
            self._session.query(Customer)
            .filter(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.email.ilike(pattern),
                    Customer.code.ilike(pattern),
                )
            )
            .order_by(func.similarity(Customer.name, query).desc())
            .limit(limit)
            .all()
        )
