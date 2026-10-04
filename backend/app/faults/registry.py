"""Fault catalogue (§27): known types, targets, and trigger validation.

A fault plan is `{type, target, trigger, params}`: reproducible from a
seed and trigger spec. `trigger` supports `{nth_call: N}` (fire on the Nth
matching call, default 1). `params` carries per-fault options
(`delay_seconds`, `after_commit`, `field`, `message`).
"""

from app.core.exceptions import UnprocessableError

FIRING_FAULTS = frozenset(
    {
        "HTTP_500_BEFORE_COMMIT",
        "HTTP_500_AFTER_COMMIT",
        "TIMEOUT",
        "VALIDATION_ERROR",
        "DUPLICATE_EFFECT",
        "SESSION_EXPIRY",
    }
)

UI_FAULTS = frozenset(
    {
        "STALE_ELEMENT",
        "REMOVED_SEARCH_FIELD",
        "DOM_DRIFT",
    }
)

KNOWN_FAULTS = FIRING_FAULTS | UI_FAULTS

# Targets are mutation families (each service checks its own target, so a
# session fault is armed against the family's target, e.g. S9 arms
# SESSION_EXPIRY on ops.replacements).
KNOWN_TARGETS = frozenset(
    {
        "ops.replacements",
        "ops.refunds",
        "ops.notes",
        "ops.reply",
        "ops.status",
        "ops.customer_search",
    }
)

BEFORE_TYPES = frozenset(
    {
        "HTTP_500_BEFORE_COMMIT",
        "TIMEOUT",
        "VALIDATION_ERROR",
        "DUPLICATE_EFFECT",
        "SESSION_EXPIRY",
    }
)

AFTER_TYPES = frozenset(
    {
        "HTTP_500_AFTER_COMMIT",
        "TIMEOUT",
    }
)


def validate_plan(fault_type: str, target: str, trigger: dict) -> None:
    """Reject unknown faults, targets, and malformed triggers (422)."""
    if fault_type not in KNOWN_FAULTS:
        raise UnprocessableError(f"unknown fault type: {fault_type}")
    if target not in KNOWN_TARGETS:
        raise UnprocessableError(f"unknown fault target: {target}")
    nth_call = trigger.get("nth_call", 1)
    if not isinstance(nth_call, int) or nth_call < 1:
        raise UnprocessableError("trigger.nth_call must be a positive integer")


def nth_call_of(trigger: dict) -> int:
    """1-based call number on which the plan fires."""
    nth = trigger.get("nth_call", 1)
    return nth if isinstance(nth, int) and nth >= 1 else 1
