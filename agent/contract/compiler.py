"""Task-contract compiler: proposals + DB facts to validated contracts.

Pure and deterministic: the LLM interpretation proposes, entity
resolution binds IDs from read-tool facts, and this module decides. No
network, no database, no model calls — every branch is unit-testable.

Outcome rules:
- `unsupported` interpretation, empty mappable effects, or any effect
  outside the registry → `unsupported` (graph ends INCONCLUSIVE).
- Cancellation language with a bound ticket but no clear effect mapping
  → `ambiguous` (scope question for the operator, oracle CLARIFY).
- Unresolved entities or untraceable amounts → `ambiguous`
  (clarification), never a guess.
- Conflicting ownership (bound triple disagrees) is NOT a question: the
  contract compiles `ok` with the conflict recorded in traceability, and
  the deterministic policy check BLOCKs it (P-OWN-001) with zero commits.
- Otherwise every effect is instantiated with bound IDs, validated
  against its registry schema, and the contract is `ok`.
"""

import re

from agent.contract.effect_registry import EffectType
from agent.contract.models import (
    BASE_CAPABILITIES,
    Contract,
    EntityResolution,
    ExpectedEffect,
)
from agent.contract.validators import (
    ContractValidationError,
    UntraceableAmountError,
    validate_amount_traceable,
    validate_effect_name,
    validate_effect_params,
)
from agent.llm.schemas import Interpretation

# Ownership conflicts compile `ok` for a deterministic policy BLOCK
# (Phase 29): they are facts from DB reads, not questions for the operator.
OWNERSHIP_PREFIX = "ownership mismatch:"
# Cancellation without a mappable effect is a scope question (S4),
# not an unsupported ask: the operator must say what "cancel" covers.
CANCELLATION_HINTS = ("cancel", "cancellation", "void")

# "mark the ticket resolved/closed/reopened..." — status words bind the target.
STATUS_WORDS = {
    "open": "open",
    "reopen": "open",
    "reopened": "open",
    "progress": "in_progress",
    "in progress": "in_progress",
    "waiting": "waiting_on_customer",
    "resolve": "resolved",
    "resolved": "resolved",
    "close": "closed",
    "closed": "closed",
}


def snapshot_scope(contract: Contract) -> dict:
    """Verifier scope: the entities this contract may touch (Phase 21)."""
    scope = {"customer_ids": [], "order_ids": [], "ticket_ids": []}
    if contract.customer_id:
        scope["customer_ids"].append(contract.customer_id)
    if contract.order_id:
        scope["order_ids"].append(contract.order_id)
    if contract.ticket_id:
        scope["ticket_ids"].append(contract.ticket_id)
    return scope


def policy_scope(contract: Contract) -> dict:
    """Policy scope: exactly what P-CAP-001/P-OWN-001 enforce (Phase 15)."""
    return {
        "customer_id": contract.customer_id,
        "order_id": contract.order_id,
        "ticket_id": contract.ticket_id,
        "capabilities": list(contract.capabilities),
        "effects": [effect.effect for effect in contract.effects],
    }


def traceability(
    operator_amounts_paise: list[int],
    resolution: EntityResolution,
    ownership_conflict: list[str] | None = None,
) -> dict:
    """Fact provenance: amounts from the operator text, bindings from DB reads."""
    record = {
        "amounts_paise": [
            {"amount_paise": amount, "source": "operator_task_text"}
            for amount in operator_amounts_paise
        ],
        "bindings": {
            "customer_id": "database_read" if resolution.customer else "unbound",
            "order_id": "database_read" if resolution.order else "unbound",
            "ticket_id": "database_read" if resolution.ticket else "unbound",
        },
        "untrusted_inputs_ignored": ["ticket_body", "page_text"],
    }
    if ownership_conflict:
        record["ownership_conflict"] = list(ownership_conflict)
    return record


def compile_contract(
    task_id: str,
    task_text: str,
    interpretation: Interpretation,
    resolution: EntityResolution,
    operator_amounts_paise: list[int],
) -> Contract:
    """Bind one interpretation to a validated contract (or a safe end)."""
    ownership_conflicts = [
        item for item in resolution.ambiguities if item.startswith(OWNERSHIP_PREFIX)
    ]
    hard_blocks = [item for item in resolution.ambiguities if not item.startswith(OWNERSHIP_PREFIX)]
    hard_blocks.extend(f"unknown code: {code}" for code in resolution.unmatched_codes)

    unknown_effects = [name for name in interpretation.requested_effects if not _known_effect(name)]
    if interpretation.unsupported or not interpretation.requested_effects or unknown_effects:
        if _is_cancellation(task_text) and resolution.ticket is not None:
            hard_blocks.append("cancellation scope unclear: full order or single item?")
            return _ambiguous(
                task_id, interpretation, resolution, hard_blocks + ownership_conflicts
            )
        return _unsupported(task_id, interpretation, resolution, unknown_effects)

    effects: list[ExpectedEffect] = []
    for name in interpretation.requested_effects:
        try:
            effects.append(
                _instantiate(name, task_text, interpretation, resolution, operator_amounts_paise)
            )
        except (ContractValidationError, UntraceableAmountError) as exc:
            hard_blocks.append(str(exc))

    if hard_blocks:
        return _ambiguous(task_id, interpretation, resolution, hard_blocks + ownership_conflicts)
    capabilities = list(BASE_CAPABILITIES) + sorted({effect.capability for effect in effects})
    contract = Contract(
        task_id=task_id,
        goal=interpretation.goal,
        customer_id=_entity_id(resolution.customer),
        order_id=_entity_id(resolution.order),
        ticket_id=_entity_id(resolution.ticket),
        effects=effects,
        capabilities=capabilities,
        ambiguity=[],
        status="ok",
    )
    contract.snapshot_scope = snapshot_scope(contract)
    contract.policy_scope = policy_scope(contract)
    contract.traceability = traceability(
        operator_amounts_paise, resolution, ownership_conflicts or None
    )
    return contract


def _instantiate(
    name: str,
    task_text: str,
    interpretation: Interpretation,
    resolution: EntityResolution,
    operator_amounts_paise: list[int],
) -> ExpectedEffect:
    """Bind one effect's parameters from resolution + operator facts."""
    definition = validate_effect_name(name)
    effect = definition.effect
    if effect == EffectType.REPLACEMENT_CREATE:
        params = {
            "order_id": _require(resolution.order, "order"),
            "order_item_id": _require_item(resolution),
            "ticket_id": _require(resolution.ticket, "ticket"),
        }
        reason = interpretation.summary
        if reason:
            params["reason"] = reason
    elif effect == EffectType.REFUND_CREATE:
        params = {
            "order_id": _require(resolution.order, "order"),
            "ticket_id": _require(resolution.ticket, "ticket"),
            "amount_paise": _require_amount(task_text, operator_amounts_paise),
        }
    elif effect == EffectType.TICKET_NOTE:
        params = {
            "ticket_id": _require(resolution.ticket, "ticket"),
            "kind": "internal",
            "body": _require_body(task_text),
        }
    elif effect == EffectType.TICKET_REPLY:
        params = {
            "ticket_id": _require(resolution.ticket, "ticket"),
            "body": _require_body(task_text),
        }
    elif effect == EffectType.TICKET_STATUS:
        params = {
            "ticket_id": _require(resolution.ticket, "ticket"),
            "to_status": _require_status(task_text),
        }
    else:  # pragma: no cover — registry is closed; get_effect guards.
        raise ContractValidationError(f"effect outside registry: {name!r}")
    validated = validate_effect_params(definition.effect.value, params)
    return ExpectedEffect(
        effect=definition.effect.value, params=validated, capability=definition.capability
    )


def _known_effect(name: str) -> bool:
    try:
        validate_effect_name(name)
    except ContractValidationError:
        return False
    return True


def _is_cancellation(task_text: str) -> bool:
    lowered = task_text.lower()
    return any(hint in lowered for hint in CANCELLATION_HINTS)


def _entity_id(entity: dict | None) -> str | None:
    return entity.get("id") if entity else None


def _require(entity: dict | None, kind: str) -> str:
    if entity is None or not entity.get("id"):
        raise ContractValidationError(f"unresolved {kind}: cannot bind effect")
    return entity["id"]


def _require_item(resolution: EntityResolution) -> str:
    items = (resolution.order or {}).get("items", []) if resolution.order else []
    if not items:
        raise ContractValidationError("order has no items to replace")
    return items[0]["id"]


def _require_amount(task_text: str, operator_amounts_paise: list[int]) -> int:
    if len(operator_amounts_paise) != 1:
        raise ContractValidationError(
            f"refund needs exactly one operator amount, found {len(operator_amounts_paise)}"
        )
    amount = operator_amounts_paise[0]
    validate_amount_traceable(amount, operator_amounts_paise)
    return amount


def _require_body(task_text: str) -> str:
    match = re.search(r"'([^']{3,})'|\"([^\"]{3,})\"", task_text)
    if match is None:
        raise ContractValidationError("note needs quoted body text from the operator")
    return (match.group(1) or match.group(2)).strip()


def _require_status(task_text: str) -> str:
    lowered = task_text.lower()
    for word, status in STATUS_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return status
    raise ContractValidationError("status change needs a target status word")


def _ambiguous(
    task_id: str,
    interpretation: Interpretation,
    resolution: EntityResolution,
    ambiguities: list[str],
) -> Contract:
    """Park for the operator (graph routes to clarification)."""
    contract = Contract(
        task_id=task_id,
        goal=interpretation.goal,
        customer_id=_entity_id(resolution.customer),
        order_id=_entity_id(resolution.order),
        ticket_id=_entity_id(resolution.ticket),
        effects=[],
        capabilities=list(BASE_CAPABILITIES),
        ambiguity=ambiguities,
        status="ambiguous",
    )
    contract.snapshot_scope = snapshot_scope(contract)
    contract.policy_scope = policy_scope(contract)
    return contract


def _unsupported(
    task_id: str,
    interpretation: Interpretation,
    resolution: EntityResolution,
    unknown_effects: list[str],
) -> Contract:
    """No registry mapping (graph ends INCONCLUSIVE, never improvised)."""
    notes = ["no registry effect fits this task"]
    notes.extend(f"effect outside registry: {name!r}" for name in unknown_effects)
    contract = Contract(
        task_id=task_id,
        goal=interpretation.goal,
        customer_id=_entity_id(resolution.customer),
        order_id=_entity_id(resolution.order),
        ticket_id=_entity_id(resolution.ticket),
        effects=[],
        capabilities=list(BASE_CAPABILITIES),
        ambiguity=notes,
        status="unsupported",
    )
    contract.snapshot_scope = snapshot_scope(contract)
    contract.policy_scope = policy_scope(contract)
    return contract
