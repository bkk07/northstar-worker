"""Phase 17: table-driven classifier tests for all 14 types (pure, no DB).

Each row is (tool, result, observation) → expected taxonomy type. The
three plan-pinned mappings get named tests; every other type gets at
least one row in the table.
"""

import pytest

from agent.failures import taxonomy
from agent.failures.classifier import classify, classify_failure
from agent.failures.signals import FailureSignals


def _fail(tool="browser_observe", status=None, error="", exception="", **extra):
    result = {
        "ok": False,
        "error": error,
        "error_type": exception,
        "mutated": extra.pop("mutated", False),
        "payload": {"status": status} if status is not None else {},
    }
    return classify_failure({"tool": tool}, {**result, **extra}, {"error": error})


CASES = [
    # (tool, status, error/exception markers, expected)
    ("get_order", 500, "internal server error", taxonomy.NETWORK_ERROR),
    ("search_customer", 503, "service unavailable", taxonomy.NETWORK_ERROR),
    ("browser_observe", None, "connection refused", taxonomy.NETWORK_ERROR),
    ("browser_submit", 500, "internal server error", taxonomy.UNKNOWN_OUTCOME),
    ("browser_submit", None, "timeout waiting for response", taxonomy.UNKNOWN_OUTCOME),
    ("browser_submit", None, "transport closed", taxonomy.UNKNOWN_OUTCOME),
    ("browser_observe", None, "timeout waiting for response", taxonomy.TIMEOUT),
    ("get_ticket", None, "ActionTimeout", taxonomy.TIMEOUT),
    ("browser_submit", 422, "validation failed: amount is invalid", taxonomy.VALIDATION_ERROR),
    ("get_order", 404, "not found", taxonomy.NOT_FOUND),
    (
        "browser_submit",
        409,
        "order item already has an active replacement",
        taxonomy.CONFLICT_DUPLICATE,
    ),
    ("browser_submit", None, "idempotency key already used", taxonomy.CONFLICT_DUPLICATE),
    ("browser_navigate", None, "ops session expired or invalid", taxonomy.SESSION_EXPIRED),
    ("browser_click", 401, "unauthorized", taxonomy.SESSION_EXPIRED),
    ("browser_fill", 403, "forbidden", taxonomy.FORBIDDEN),
    ("browser_click", None, "StaleReference: page moved", taxonomy.STALE_REFERENCE),
    ("browser_fill", None, "unknown ref e9", taxonomy.ELEMENT_NOT_FOUND),
    ("browser_click", None, "ElementNotFound", taxonomy.ELEMENT_NOT_FOUND),
    ("browser_observe", None, "search field removed from page", taxonomy.DOM_DRIFT),
    (
        "browser_submit",
        None,
        "token_denied: submit requires a policy token",
        taxonomy.POLICY_BLOCKED,
    ),
    ("browser_navigate", None, "outside the url guard", taxonomy.GUARD_VIOLATION),
    ("browser_open", None, "browser target closed", taxonomy.BROWSER_UNAVAILABLE),
]


@pytest.mark.parametrize("tool,status,error,expected", CASES)
def test_taxonomy_table(tool, status, error, expected):
    """Every row maps to its taxonomy type (first match wins)."""
    failure_type, found = _fail(tool, status=status, error=error)
    assert failure_type == expected
    assert found["tool"] == tool and found["status"] == status


def test_write_500_is_unknown_outcome():
    """Plan pin: a 500 on commit may have landed (never blind-retry)."""
    assert classify(FailureSignals(tool="browser_submit", status=500)) == (taxonomy.UNKNOWN_OUTCOME)


def test_read_500_is_network_error():
    """Plan pin: a 500 on a read mutated nothing (safe to retry)."""
    assert classify(FailureSignals(tool="get_order", status=500)) == taxonomy.NETWORK_ERROR


def test_login_redirect_is_session_expired():
    """Plan pin: a login redirect means re-login, then retry."""
    assert classify(FailureSignals(tool="browser_navigate", login_redirect=True)) == (
        taxonomy.SESSION_EXPIRED
    )


def test_unknown_outcome_never_retryable():
    """UNKNOWN_OUTCOME is the one type Phase 18 may not blind-retry."""
    assert taxonomy.UNKNOWN_OUTCOME not in taxonomy.RETRYABLE
    assert taxonomy.NETWORK_ERROR in taxonomy.RETRYABLE


def test_taxonomy_closed_at_fourteen():
    """No inventing types outside the classifier (router depends on it)."""
    assert len(taxonomy.ALL_TYPES) == 14
