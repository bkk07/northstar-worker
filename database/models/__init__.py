"""Model registry: importing this package registers every table.

Alembic's `env.py` imports it for `target_metadata`. No business logic.
"""

from database.models import biz, worker  # noqa: F401
from database.models.base import Base  # noqa: F401

__all__ = ["Base", "biz", "worker"]
