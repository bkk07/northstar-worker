"""JWT auth controller: register / login / me (Phase 2)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.deps import get_db
from app.schemas.auth import AuthTokenResponse, LoginRequest, MeResponse, RegisterRequest
from app.services.auth import auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=AuthTokenResponse, status_code=201)
def register(payload: RegisterRequest, session: Session = Depends(get_db)) -> dict:
    """Sign up as CUSTOMER (or SUPPORT_AGENT for the demo console)."""
    return auth_service.register(
        session,
        name=payload.name,
        email=str(payload.email),
        password=payload.password,
        role=payload.role,
    )


@router.post("/auth/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> dict:
    """Email + password login → JWT access token."""
    return auth_service.login(session, email=str(payload.email), password=payload.password)


@router.get("/auth/me", response_model=MeResponse)
def me(
    claims: dict = Depends(get_current_user), session: Session = Depends(get_db)
) -> dict:
    """Persistent-session check: profile for the bearer subject."""
    return auth_service.get_me(session, user_id=str(claims["sub"]))
