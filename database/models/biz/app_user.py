"""Phase 2 application users (`biz.app_users`).

Separate from the sandbox `ops_sessions` cookie auth and from the
commerce `customers` profile table: this is the JWT identity store for
the 10-phase prototype (spec §9 `users`, Phase 2).
"""

import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk

CUSTOMER = "CUSTOMER"
SUPPORT_AGENT = "SUPPORT_AGENT"
ROLES = (CUSTOMER, SUPPORT_AGENT)


class AppUser(UUIDPk, CreatedAt, Base):
    """Login identity with Argon2 password hash and role."""

    __tablename__ = "app_users"
    __table_args__ = {"schema": "biz"}

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=CUSTOMER)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
