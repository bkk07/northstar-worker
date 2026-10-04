"""Business customers (`biz.customers`)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk


class Customer(UUIDPk, CreatedAt, Base):
    """Customer with a human code; name search uses the trigram index.

    The trigram GIN index on `lower(name)` is PG-specific DDL and lives in
    migration 0001 (raw SQL), not in the model.
    """

    __tablename__ = "customers"
    __table_args__ = {"schema": "biz"}

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
