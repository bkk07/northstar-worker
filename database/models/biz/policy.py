"""Policy rules table (`biz.policies`, read by the policy engine)."""

from typing import Any

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, UUIDPk


class Policy(UUIDPk, Base):
    """Versioned policy rule (thresholds live here, defaults in code)."""

    __tablename__ = "policies"
    __table_args__ = {"schema": "biz"}

    rule_key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
