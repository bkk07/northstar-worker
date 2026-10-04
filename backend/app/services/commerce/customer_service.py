"""Customer read service."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.commerce.customer_repository import CustomerRepository
from app.schemas.commerce.customer import CustomerRead
from database.models.biz.customer import Customer


class CustomerService:
    """Customer queries (backend owns no customer writes in Phase 6)."""

    def __init__(self, session: Session) -> None:
        self._repos = CustomerRepository(session)

    def search(self, query: str) -> list[CustomerRead]:
        """Look-alike-tolerant customer search."""
        return [self._to_dto(c) for c in self._repos.search(query)]

    def get_by_id(self, customer_id: uuid.UUID) -> CustomerRead:
        """One customer or 404."""
        customer = self._repos.get_by_id(Customer, customer_id)
        if customer is None:
            raise NotFoundError(f"customer {customer_id} not found")
        return self._to_dto(customer)

    @staticmethod
    def _to_dto(customer: Customer) -> CustomerRead:
        return CustomerRead(
            id=customer.id, code=customer.code, name=customer.name, email=customer.email
        )
