"""Phase 2 authentication service (spec: register / login / me).

Business rules live here; the controller only maps HTTP, the
repository only queries. Passwords are Argon2 hashes, sessions are
stateless JWTs (24h).
"""

from sqlalchemy.orm import Session

from app.core import auth as auth_core
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.repositories.auth.user_repository import UserRepository
from database.models.biz.app_user import ROLES


def register(
    session: Session, *, name: str, email: str, password: str, role: str = "CUSTOMER"
) -> dict:
    """Create a user and return an authenticated token bundle."""
    if role not in ROLES:
        raise UnauthorizedError("unknown role")
    repo = UserRepository(session)
    if repo.get_by_email(email) is not None:
        raise ConflictError("email already registered")
    row = repo.create(
        name=name.strip(),
        email=email,
        password_hash=auth_core.hash_password(password),
        role=role,
    )
    session.commit()
    session.refresh(row)
    return _bundle(row)


def login(session: Session, *, email: str, password: str) -> dict:
    """Verify credentials and return an authenticated token bundle."""
    row = UserRepository(session).get_by_email(email)
    if row is None or not auth_core.verify_password(row.password_hash, password):
        raise UnauthorizedError("invalid email or password")
    return _bundle(row)


def get_me(session: Session, *, user_id: str) -> dict:
    """Load the profile for an authenticated subject."""
    row = UserRepository(session).get_by_id(user_id)
    if row is None:
        raise NotFoundError("user not found")
    return {"id": str(row.id), "name": row.name, "email": row.email, "role": row.role}


def ensure_support_admin(
    session: Session, *, email: str, password: str, name: str = "Admin"
) -> dict:
    """Idempotent demo seed: create the console admin if missing."""
    repo = UserRepository(session)
    row = repo.get_by_email(email)
    if row is None:
        row = repo.create(
            name=name,
            email=email,
            password_hash=auth_core.hash_password(password),
            role="SUPPORT_AGENT",
        )
        session.commit()
        session.refresh(row)
    return {"id": str(row.id), "name": row.name, "email": row.email, "role": row.role}


def _bundle(row) -> dict:
    profile = {"id": str(row.id), "name": row.name, "email": row.email, "role": row.role}
    return {
        "access_token": auth_core.create_access_token(
            user_id=str(row.id), email=row.email, role=row.role
        ),
        "token_type": "bearer",
        "user": profile,
    }
