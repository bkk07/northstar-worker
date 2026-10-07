"""Ops DTOs: session auth."""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Staff-only sandbox login (SUPPORT_AGENT JWT + staff password required)."""

    agent_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    """Issued session (token also set as httponly cookie)."""

    agent_name: str
    expires_at: datetime


class LogoutResponse(BaseModel):
    """Logout acknowledgement."""

    ok: bool = True
