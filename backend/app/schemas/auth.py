"""Phase 2 auth DTOs: register / login / me (spec §16)."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["CUSTOMER", "SUPPORT_AGENT"]


class RegisterRequest(BaseModel):
    """Customer sign-up. Prototype allows requesting SUPPORT_AGENT (demo)."""

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role = "CUSTOMER"


class LoginRequest(BaseModel):
    """Email + password login for both storefront and console."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthTokenResponse(BaseModel):
    """JWT access token plus the authenticated profile."""

    access_token: str
    token_type: str = "bearer"
    user: "MeResponse"


class MeResponse(BaseModel):
    """Authenticated profile (`GET /auth/me`)."""

    id: str
    name: str
    email: str
    role: str
