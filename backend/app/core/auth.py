"""Phase 2 JWT identity: Argon2 passwords + signed access tokens.

Router -> service -> repository stays intact: this module owns only
hashing, token minting/parsing, and the `get_current_user` dependency.
Sandbox `ops_session` cookie auth is untouched.
"""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from northstar_common.config import get_settings

_ph = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)

TOKEN_TTL = timedelta(hours=24)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Argon2-hash a plaintext password."""
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True when the password matches the Argon2 hash."""
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, ValueError, AttributeError):
        return False


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Mint a signed JWT access token (24h)."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + TOKEN_TTL).timestamp()),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT; raise 401 on any problem."""
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("invalid or expired token") from exc


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Bearer guard returning the token claims (`sub`, `email`, `role`)."""
    if creds is None or not creds.credentials:
        raise UnauthorizedError("bearer token required")
    claims = decode_access_token(creds.credentials)
    if not claims.get("sub") or not claims.get("role"):
        raise UnauthorizedError("invalid token claims")
    return claims


def require_roles(*roles: str):
    """Role guard factory (e.g. `require_roles("SUPPORT_AGENT")`)."""

    def guard(claims: dict = Depends(get_current_user)) -> dict:
        if claims.get("role") not in roles:
            raise ForbiddenError("insufficient role")
        return claims

    return guard


def require_roles_or_service(*roles: str):
    """JWT role guard with a first-party service identity escape hatch.

    The MCP worker plane is an internal service, not a user: it presents
    `Authorization: Bearer <OPERATOR_TOKEN>` (same env both sides; non-local
    deploys must set a real secret — enforced at startup). Human callers go
    through the normal JWT + role path. Anonymous callers still get 401.
    """

    def guard(
        creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> dict:
        if creds is None or not creds.credentials:
            raise UnauthorizedError("bearer token required")
        token = creds.credentials
        if token and token == get_settings().operator_token:
            return {
                "sub": "svc-mcp",
                "email": "mcp@internal",
                "role": "SERVICE",
            }
        claims = decode_access_token(token)
        if not claims.get("sub") or not claims.get("role"):
            raise UnauthorizedError("invalid token claims")
        if claims.get("role") not in roles:
            raise ForbiddenError("insufficient role")
        return claims

    return guard
