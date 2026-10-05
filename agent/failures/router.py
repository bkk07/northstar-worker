"""Recovery router: failure type → strategy (pure, Phase 18).

Every taxonomy type maps to exactly one edge-vocabulary strategy, with
a per-strategy attempt bound. When the bound is hit, the router yields
`terminate_safely` — recovery never loops forever. UNKNOWN_OUTCOME and
duplicates also terminate here; Phase 19 takes them over with probe.
"""

from agent.failures import taxonomy

# Strategy vocabulary is fixed by the graph edges (route_recover).
RE_OBSERVE = "re_observe"
RE_DISCOVER = "re_discover"
RE_PLAN = "re_plan"
RETRY = "retry"
FALLBACK_TOOL = "fallback_tool"
TERMINATE = "terminate_safely"

# Type → (strategy, max attempts before terminate).
ROUTES: dict[str, tuple[str, int]] = {
    taxonomy.NETWORK_ERROR: (RETRY, 3),
    taxonomy.TIMEOUT: (RETRY, 3),
    taxonomy.SESSION_EXPIRED: (RE_OBSERVE, 2),
    taxonomy.STALE_REFERENCE: (RE_OBSERVE, 3),
    taxonomy.ELEMENT_NOT_FOUND: (FALLBACK_TOOL, 2),
    taxonomy.DOM_DRIFT: (RE_DISCOVER, 2),
    taxonomy.VALIDATION_ERROR: (RE_OBSERVE, 2),
    taxonomy.NOT_FOUND: (RE_DISCOVER, 2),
    taxonomy.BROWSER_UNAVAILABLE: (RE_OBSERVE, 2),
    taxonomy.CONFLICT_DUPLICATE: ("probe", 2),
    taxonomy.UNKNOWN_OUTCOME: ("probe", 2),
    taxonomy.FORBIDDEN: (TERMINATE, 0),
    taxonomy.POLICY_BLOCKED: (TERMINATE, 0),
    taxonomy.GUARD_VIOLATION: (TERMINATE, 0),
}

assert set(ROUTES) == taxonomy.ALL_TYPES, "router must cover all 14 types"


def route(failure_type: str, counters: dict) -> tuple[str, int]:
    """Strategy for a failure type with used-up bounds forced to terminate."""
    strategy, limit = ROUTES.get(failure_type, (TERMINATE, 0))
    if limit and counters.get(strategy, 0) >= limit:
        return TERMINATE, counters.get(TERMINATE, 0)
    return strategy, counters.get(strategy, 0)


def backoff_ms(attempt: int, base_ms: int = 500, cap_ms: int = 5000) -> int:
    """Exponential backoff for bounded retries (0-indexed attempt)."""
    return min(cap_ms, base_ms * (2 ** max(0, attempt)))
