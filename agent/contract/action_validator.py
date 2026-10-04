"""Action validator: schema, capability, and parameter-binding checks.

Everything a `decide` proposal must survive before policy or tools see
it. Pure and fail-closed: unknown tools, out-of-scope capabilities, and
parameters that do not match the locked contract are rejected with
machine-readable errors that feed the bounded correction loop.

The tool mirror below names every registered tool with its capability
and kind. It duplicates `mcp_server/registry.py` deliberately — the
agent must never import the tool server — and a parity test fails the
build when the two drift apart.
"""

import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from agent.contract.models import Contract
from agent.llm.schemas import NextAction
from northstar_common.errors import NorthstarError

REF_PATTERN = re.compile(r"^e\d+$")

# Operational submit keys checked downstream (MCP token guard, idempotency),
# never against contract bindings.
SUBMIT_OPERATIONAL_KEYS = frozenset({"ref", "mutation_key", "token"})

# Binding keys: when present, they must equal the locked contract.
BINDING_KEYS = frozenset({"order_id", "ticket_id", "customer_id", "order_item_id", "amount_paise"})


class ActionValidationError(NorthstarError):
    """A proposal failed schema, capability, or binding checks."""

    code = "ACTION_INVALID"


@dataclass(frozen=True)
class ToolMeta:
    """Agent-side tool facts: capability gate and journal kind."""

    name: str
    capability: str
    kind: str  # "read" | "write" (only browser_submit writes)
    side_effect: str  # "none" | "read" | "write" (actions.side_effect)


TOOL_META: dict[str, ToolMeta] = {
    "search_customer": ToolMeta("search_customer", "read", "read", "none"),
    "get_customer": ToolMeta("get_customer", "read", "read", "none"),
    "search_order": ToolMeta("search_order", "read", "read", "none"),
    "get_order": ToolMeta("get_order", "read", "read", "none"),
    "get_ticket": ToolMeta("get_ticket", "read", "read", "none"),
    "get_policy": ToolMeta("get_policy", "read", "read", "none"),
    "api_get": ToolMeta("api_get", "read.fallback", "read", "none"),
    "inspect_state": ToolMeta("inspect_state", "probe", "read", "none"),
    "browser_open": ToolMeta("browser_open", "browser", "read", "read"),
    "browser_navigate": ToolMeta("browser_navigate", "browser", "read", "read"),
    "browser_observe": ToolMeta("browser_observe", "browser", "read", "none"),
    "browser_click": ToolMeta("browser_click", "browser", "read", "read"),
    "browser_fill": ToolMeta("browser_fill", "browser", "read", "read"),
    "browser_submit": ToolMeta("browser_submit", "per effect", "write", "write"),
    "browser_back": ToolMeta("browser_back", "browser", "read", "read"),
    "browser_screenshot": ToolMeta("browser_screenshot", "browser", "read", "none"),
}


@dataclass
class ValidationOutcome:
    """Validator verdict with correctable errors for the feedback loop."""

    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_action(action: dict, contract: Contract) -> ValidationOutcome:
    """Schema → known tool → capability → binding (first failure wins)."""
    try:
        proposal = NextAction.model_validate(action)
    except ValidationError as exc:
        return ValidationOutcome(
            valid=False, errors=[f"schema: {err['loc']}: {err['msg']}" for err in exc.errors()]
        )
    meta = TOOL_META.get(proposal.tool)
    if meta is None:
        return ValidationOutcome(valid=False, errors=[f"unknown tool: {proposal.tool}"])
    if proposal.tool == "browser_submit":
        return _validate_submit(proposal, contract)
    capability_error = _check_capability(meta.capability, contract)
    if capability_error is not None:
        return ValidationOutcome(valid=False, errors=[capability_error])
    ref_error = _check_refs(proposal)
    if ref_error is not None:
        return ValidationOutcome(valid=False, errors=[ref_error])
    return ValidationOutcome(valid=True)


def _validate_submit(proposal: NextAction, contract: Contract) -> ValidationOutcome:
    """Commits bind exactly: effect in contract, bindings equal, refs shaped."""
    params = proposal.params
    effect_name = params.get("effect", "")
    match = next((e for e in contract.effects if e.effect == effect_name), None)
    if match is None:
        return ValidationOutcome(
            valid=False,
            errors=[f"capability: submit effect {effect_name!r} outside contract scope"],
        )
    if match.capability not in contract.capabilities:
        return ValidationOutcome(
            valid=False,
            errors=[f"capability: task lacks {match.capability!r}"],
        )
    for key, expected in match.params.items():
        if key not in BINDING_KEYS:
            continue
        actual = params.get(key)
        if actual != expected:
            return ValidationOutcome(
                valid=False,
                errors=[f"binding: {key}={actual!r} does not match contract {expected!r}"],
            )
    ref = params.get("ref", "")
    if not isinstance(ref, str) or not REF_PATTERN.match(ref):
        return ValidationOutcome(valid=False, errors=[f"schema: bad submit ref {ref!r}"])
    return ValidationOutcome(valid=True)


def _check_capability(capability: str, contract: Contract) -> str | None:
    if capability not in contract.capabilities:
        return f"capability: task lacks {capability!r}"
    return None


def _check_refs(proposal: NextAction) -> str | None:
    ref = proposal.params.get("ref")
    if ref is None:
        return None
    if not isinstance(ref, str) or not REF_PATTERN.match(ref):
        return f"schema: bad ref {ref!r} (observe first, then act)"
    return None
