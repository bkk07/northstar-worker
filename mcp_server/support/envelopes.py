"""Uniform tool envelopes + safe error mapping (spec Phase 7).

Reads return `{"ok": True, ...dto}`; failures return
`{"ok": False, "code": ..., "error": ...}` — never tracebacks, never raw
SQL. Domain errors come from `AppError` (code + message); anything else is
an internal failure with no details leaked.
"""

import uuid

from app.core.exceptions import AppError


def ok(**data) -> dict:
    """Success envelope."""
    return {"ok": True, **data}


def fail(error: str, *, code: str = "TOOL_ERROR") -> dict:
    """Failure envelope."""
    return {"ok": False, "code": code, "error": error}


def parse_uuid(value: str, name: str) -> uuid.UUID:
    """Strict UUID or ValueError (validated before any DB work)."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise ValueError(f"invalid {name}: {value!r}") from None


def require_text(value: str, name: str, *, minimum: int = 1, maximum: int = 2000) -> str:
    """Non-empty trimmed text or ValueError (validated before any DB work)."""
    text = (value or "").strip()
    if len(text) < minimum:
        raise ValueError(f"{name} is too short (minimum {minimum} characters)")
    if len(text) > maximum:
        raise ValueError(f"{name} is too long (maximum {maximum} characters)")
    return text


def run_guarded(fn, *args, **kwargs) -> dict:
    """Run a service call, mapping domain errors to failure envelopes."""
    try:
        return fn(*args, **kwargs)
    except AppError as exc:
        return fail(exc.message, code=exc.code)
    except ValueError as exc:
        return fail(str(exc), code="INVALID_ARGUMENT")
    except Exception:
        return fail("internal tool failure", code="INTERNAL_ERROR")
