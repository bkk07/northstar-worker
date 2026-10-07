"""Ops auth controller: login / logout (session cookie)."""

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import COOKIE_NAME, create_session, revoke_session
from app.schemas.ops.auth import LoginRequest, LoginResponse, LogoutResponse
from app.services.auth import auth_service

router = APIRouter(tags=["ops-auth"])

_staff = require_roles("SUPPORT_AGENT")


@router.post("/api/ops/auth/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> LoginResponse:
    """Staff-only sandbox login: JWT staff + password must verify.

    The legacy dummy `agent_name` login is removed. The caller must present
    a SUPPORT_AGENT JWT and the staff password; the ops session is bound to
    the JWT identity (staff email), not an arbitrary agent name.
    """
    staff_email = str(claims.get("email", ""))
    if not payload.password:
        raise UnauthorizedError("staff password required")
    try:
        auth_service.login(session, email=staff_email, password=payload.password)
    except Exception as exc:
        raise UnauthorizedError("invalid staff credentials") from exc
    token, expires_at = create_session(session, staff_email)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=24 * 3600)
    return LoginResponse(agent_name=staff_email, expires_at=expires_at)


@router.post("/api/ops/auth/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    session: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> LogoutResponse:
    """Revoke the session and clear the cookie."""
    revoke_session(session, token)
    response.delete_cookie(COOKIE_NAME)
    return LogoutResponse(ok=True)
