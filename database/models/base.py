"""Declarative base and column conventions (no business logic).

Conventions: UUID PKs, `timestamptz` timestamps, integer-paise money,
human codes in UNIQUE columns. One metadata object for Alembic.
"""

import datetime
import uuid

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base (schemas `biz` and `worker`)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPk:
    """UUID primary key mixin (all PKs are UUID)."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class CreatedAt:
    """Creation timestamp mixin (`timestamptz`, server default now())."""

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
