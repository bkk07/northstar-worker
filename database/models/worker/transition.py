"""Task state machine in the database (`worker.allowed_transitions`).

Rows mirror `agent.runtime.transitions.ALLOWED_TRANSITIONS`; a trigger
rejects any `tasks.status` change outside this table. A test asserts the
two stay in sync, so the code stays the source of truth.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class AllowedTransition(Base):
    """One legal (from_status, to_status) pair."""

    __tablename__ = "allowed_transitions"
    __table_args__ = {"schema": "worker"}

    from_status: Mapped[str] = mapped_column(String(40), primary_key=True)
    to_status: Mapped[str] = mapped_column(String(40), primary_key=True)
