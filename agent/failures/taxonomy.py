"""Failure taxonomy: the 14 deterministic failure types (Phase 17).

Recovery (Phase 18) routes on these names; nothing else may invent a
failure type. Each type says whether the failed action is safe to retry
as-is — UNKNOWN_OUTCOME is never safe (the commit may have landed, so
only probe-then-reconcile may follow).
"""

# All 14 types. The classifier is the only producer (plus POLICY_BLOCKED
# from policy mapping); the router consumes them in Phase 18.
NETWORK_ERROR = "network_error"
UNKNOWN_OUTCOME = "unknown_outcome"
TIMEOUT = "timeout"
VALIDATION_ERROR = "validation_error"
NOT_FOUND = "not_found"
CONFLICT_DUPLICATE = "conflict_duplicate"
SESSION_EXPIRED = "session_expired"
FORBIDDEN = "forbidden"
STALE_REFERENCE = "stale_reference"
ELEMENT_NOT_FOUND = "element_not_found"
DOM_DRIFT = "dom_drift"
POLICY_BLOCKED = "policy_blocked"
GUARD_VIOLATION = "guard_violation"
BROWSER_UNAVAILABLE = "browser_unavailable"

ALL_TYPES = frozenset(
    {
        NETWORK_ERROR,
        UNKNOWN_OUTCOME,
        TIMEOUT,
        VALIDATION_ERROR,
        NOT_FOUND,
        CONFLICT_DUPLICATE,
        SESSION_EXPIRED,
        FORBIDDEN,
        STALE_REFERENCE,
        ELEMENT_NOT_FOUND,
        DOM_DRIFT,
        POLICY_BLOCKED,
        GUARD_VIOLATION,
        BROWSER_UNAVAILABLE,
    }
)

assert len(ALL_TYPES) == 14, "taxonomy must stay exactly 14 types"

# Safe to retry the same action unchanged (Phase 18 reads this).
RETRYABLE = frozenset(
    {
        NETWORK_ERROR,
        TIMEOUT,
        SESSION_EXPIRED,
        STALE_REFERENCE,
        ELEMENT_NOT_FOUND,
        DOM_DRIFT,
        BROWSER_UNAVAILABLE,
    }
)
