"""Recovery strategies: what each route changes in the run state.

Strategies rewrite state, never call tools (the graph edges do the
acting). Fallbacks stay inside the contract's capability scope — a
fallback outside scope degrades to terminate_safely, never to an
unscoped tool call.
"""

from agent.contract.models import Contract
from agent.failures import router

# Search-shaped reads and their api_get fallback (path + param mapping).
# UI search dies (S7: removed field) → the read API answers instead.
SEARCH_FALLBACKS = {
    "search_customer": ("/api/read/customers", ("q",)),
    "search_order": ("/api/read/orders", ("customer_id", "q")),
    "get_customer": ("/api/read/customers/{customer_id}", ()),
    "get_order": ("/api/read/orders/{order_id}", ()),
    "get_ticket": ("/api/read/tickets/{ticket_id}", ()),
    "get_policy": ("/api/read/policies", ()),
}

FALLBACK_CAPABILITY = "read.fallback"


def apply_strategy(
    strategy: str,
    state: dict,
    contract: Contract | None,
    failure_type: str,
) -> dict:
    """State delta for a routed strategy (pure; service persists/audits)."""
    if strategy == router.FALLBACK_TOOL:
        return _fallback(state, contract, failure_type)
    if strategy == router.RE_PLAN:
        return {"plan": [], "cursor": 0}
    if strategy == router.RE_DISCOVER:
        delta: dict = {"cursor": state.get("cursor", 0)}
        action = dict(state.get("last_action", {}))
        action.pop("ref", None)
        delta["last_action"] = action
        return delta
    if strategy == router.RE_OBSERVE:
        delta = {}
        if failure_type == "session_expired":
            delta["relogin"] = True
        if state.get("validation_error"):
            delta["validation_failures"] = state.get("validation_failures", 0) + 1
        return delta
    if strategy == router.RETRY:
        used = state.get("recovery", {}).get("counters", {}).get(router.RETRY, 0)
        return {"backoff_ms": router.backoff_ms(used)}
    return {}


def _fallback(state: dict, contract: Contract | None, failure_type: str) -> dict:
    """Rewrite a dead UI search as an api_get (scope-checked)."""
    _ = failure_type
    action = dict(state.get("last_action", {}))
    tool = action.get("tool", "")
    mapping = SEARCH_FALLBACKS.get(tool)
    if mapping is None or contract is None or FALLBACK_CAPABILITY not in contract.capabilities:
        return {"recovery_override": router.TERMINATE}
    path_template, keys = mapping
    raw = action.get("params", {})
    params = {k: raw.get(k) for k in keys if raw.get(k) is not None}
    try:
        path = path_template.format(**raw)
    except (KeyError, IndexError):
        return {"recovery_override": router.TERMINATE}
    return {
        "last_action": {
            "tool": "api_get",
            "params": {"path": path, "params": params},
            "rationale": f"fallback: {tool} unreachable, retrying via read API",
        }
    }
