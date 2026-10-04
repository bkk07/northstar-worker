"""Backend error hierarchy with HTTP mapping (Phase 6).

Services raise these; `main.py` translates them to JSON responses.
Business-rule violations are 422, duplicates 409, auth failures 401.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base error carrying an HTTP status and machine code."""

    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message or self.code


class NotFoundError(AppError):
    """Entity does not exist."""

    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    """Duplicate business identity (unique constraint would fire)."""

    status_code = 409
    code = "CONFLICT"


class UnauthorizedError(AppError):
    """Missing or invalid ops session."""

    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    """Valid identity, insufficient authority (control plane token)."""

    status_code = 403
    code = "FORBIDDEN"


class UnprocessableError(AppError):
    """Business-rule violation (ownership, amounts, bad status)."""

    status_code = 422
    code = "UNPROCESSABLE"


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Render AppError as a JSON problem body."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )
