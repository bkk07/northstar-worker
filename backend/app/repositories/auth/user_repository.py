"""`biz.app_users` data access (no business logic)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.biz.app_user import AppUser


class UserRepository:
    """Thin queries over `biz.app_users`."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def get_by_email(self, email: str) -> AppUser | None:
        return self._s.scalars(
            select(AppUser).where(AppUser.email == email.lower())
        ).first()

    def get_by_id(self, user_id: uuid.UUID | str) -> AppUser | None:
        return self._s.get(AppUser, user_id)

    def create(
        self, *, name: str, email: str, password_hash: str, role: str
    ) -> AppUser:
        row = AppUser(name=name, email=email.lower(), password_hash=password_hash, role=role)
        self._s.add(row)
        self._s.flush()
        return row
