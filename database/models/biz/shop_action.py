"""Phase 7 mock business actions (`biz.shop_actions`).

Uniform record for agent-executed mock actions (refund / return / replace /
cancel) against Phase 4 orders: one row per mutation key, so a retried tool
call collides instead of duplicating (same convention as `biz.refunds`).
Status mutations on the order itself (CANCELLED / RETURNED) live on
`biz.shop_orders.status`; the money movement is mock, the row is the proof
(Phase 9 verifies by re-reading it).
"""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, CreatedAt, UUIDPk

ACTION_REFUND = "REFUND"
ACTION_RETURN = "RETURN"
ACTION_REPLACE = "REPLACE"
ACTION_CANCEL = "CANCEL"

ACTION_DONE = "DONE"


class ShopAction(UUIDPk, CreatedAt, Base):
    """One executed mock action, idempotent by mutation key."""

    __tablename__ = "shop_actions"
    __table_args__ = (
        Index("ix_shop_actions_order_id", "order_id"),
        {"schema": "biz"},
    )

    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.customer_tickets.id"), nullable=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("biz.shop_orders.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ACTION_DONE)
    mutation_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
