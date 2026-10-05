"""Failure signals: the classifier's inputs, extracted deterministically.

One signal bundle per failed tool call: what ran, whether a commit may
have happened, the HTTP status when one exists, the exception name, and
page markers (login redirect, error banner). Pure extraction — the
classifier decides, this module only observes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureSignals:
    """Everything the taxonomy needs (tool, mutation, status, exception, page)."""

    tool: str = ""
    mutated: bool = False
    status: int | None = None
    exception: str = ""
    error_text: str = ""
    login_redirect: bool = False
    error_banner: bool = False


def extract(action: dict, result: dict, observation: dict) -> FailureSignals:
    """Pull signals from the executed action and its failed outcome."""
    payload = result.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}
    error_text = " ".join(
        [
            str(result.get("error", "")),
            str(payload.get("body", "")),
            str(observation.get("error", "")),
        ]
    ).lower()
    status = payload.get("status", observation.get("status"))
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None
    url = str(payload.get("url", observation.get("url", ""))).lower()
    return FailureSignals(
        tool=str(action.get("tool", "")),
        mutated=bool(result.get("mutated", False)),
        status=status,
        exception=str(result.get("error_type", "")),
        error_text=error_text[:500],
        login_redirect="/ops/login" in url or "login" in url and "session" in error_text,
        error_banner="banner" in error_text or "error" in error_text and "page" in error_text,
    )


def describe(signals: FailureSignals) -> dict:
    """JSON-safe signal bundle (journal + audit payloads)."""
    return {
        "tool": signals.tool,
        "mutated": signals.mutated,
        "status": signals.status,
        "exception": signals.exception,
        "login_redirect": signals.login_redirect,
        "error_banner": signals.error_banner,
    }
