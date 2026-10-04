"""Ops auth controller: login / logout (session cookie)."""

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import COOKIE_NAME, create_session, revoke_session
from app.schemas.ops.auth import LoginRequest, LoginResponse, LogoutResponse

router = APIRouter(tags=["ops-auth"])


@router.post("/api/ops/auth/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, response: Response, session: Session = Depends(get_db)
) -> LoginResponse:
    """Sandbox login: mint a session and set the cookie."""
    token, expires_at = create_session(session, payload.agent_name)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=24 * 3600)
    return LoginResponse(agent_name=payload.agent_name, expires_at=expires_at)


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
