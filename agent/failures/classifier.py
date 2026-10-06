"""Deterministic failure classifier (Phase 17).

Consumes (tool, mutation flag, status, exception, page signals) and
returns exactly one of the 14 taxonomy types. Order matters — first
match wins — and the three plan-pinned mappings hold:

- write + 500 → UNKNOWN_OUTCOME (the commit may have landed)
- read + 500 → NETWORK_ERROR (nothing could have mutated)
- login redirect → SESSION_EXPIRED (re-login, then retry)
"""

from agent.failures import signals as signal_module
from agent.failures import taxonomy
from agent.failures.signals import FailureSignals

WRITE_TOOLS = frozenset({"browser_submit", "refund_create", "replacement_create"})


def classify(signals: FailureSignals) -> str:
    """Map one signal bundle to its taxonomy type (pure, total)."""
    text = signals.error_text
    exception = signals.exception

    if _mentions(
        text,
        exception,
        ("token_denied", "capability_denied", "policy_blocked", "not permitted"),
    ):
        return taxonomy.POLICY_BLOCKED
    if _mentions(text, exception, ("guard", "url guard", "outside the url guard")):
        return taxonomy.GUARD_VIOLATION
    if signals.login_redirect or signals.status == 401:
        return taxonomy.SESSION_EXPIRED
    if signals.status == 401 or _mentions(
        text, exception, ("unauthorized", "session expired", "session invalid", "revoked")
    ):
        return taxonomy.SESSION_EXPIRED
    if signals.status == 403 or "forbidden" in text:
        return taxonomy.FORBIDDEN
    if signals.status == 404 or _mentions(text, exception, ("not found", "not_found", "no such")):
        return taxonomy.NOT_FOUND
    if signals.status == 409 or _mentions(
        text, exception, ("conflict", "duplicate", "already has an active", "already used")
    ):
        return taxonomy.CONFLICT_DUPLICATE
    if signals.status == 422 or _mentions(text, exception, ("validation", "rejected", "allowlist")):
        return taxonomy.VALIDATION_ERROR
    if _mentions(text, exception, ("stalereference", "stale", "page moved")):
        return taxonomy.STALE_REFERENCE
    if _mentions(text, exception, ("elementnotfound", "unknown ref", "no ref")):
        return taxonomy.ELEMENT_NOT_FOUND
    if signals.error_banner or _mentions(text, exception, ("dom drift", "removed", "banner")):
        return taxonomy.DOM_DRIFT
    if _mentions(text, exception, ("actiontimeout", "timeout", "timed out", "deadline")):
        if signals.tool in WRITE_TOOLS:
            return taxonomy.UNKNOWN_OUTCOME
        return taxonomy.TIMEOUT
    if signals.status is not None and signals.status >= 500:
        if signals.tool in WRITE_TOOLS or signals.mutated:
            return taxonomy.UNKNOWN_OUTCOME
        return taxonomy.NETWORK_ERROR
    if (
        _mentions(
            text,
            exception,
            ("browser_unavailable", "session", "target closed", "crash", "disconnected"),
        )
        and "expired" not in text
        and "invalid" not in text
    ):
        return taxonomy.BROWSER_UNAVAILABLE
    if signals.tool in WRITE_TOOLS or signals.mutated:
        return taxonomy.UNKNOWN_OUTCOME
    if exception or text.strip():
        return taxonomy.NETWORK_ERROR
    return taxonomy.NETWORK_ERROR


def classify_failure(action: dict, result: dict, observation: dict) -> tuple[str, dict]:
    """Signals + type for one failed outcome (journal/audit payloads)."""
    found = signal_module.extract(action, result, observation)
    return classify(found), signal_module.describe(found)


def _mentions(text: str, exception: str, markers: tuple[str, ...]) -> bool:
    """True when any marker appears in the error text or exception name."""
    blob = f"{text} {exception}".lower()
    return any(marker in blob for marker in markers)
