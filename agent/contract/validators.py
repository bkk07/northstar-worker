"""Contract validators: deterministic gates on effects and parameters.

Every check is pure and fail-closed: unknown effects, schema-violating
parameters, and untraceable amounts raise instead of flowing downstream.
The compiler calls these; the graph never sees an invalid contract.
"""

from pydantic import ValidationError

from agent.contract.effect_registry import UnknownEffectError, get_effect
from northstar_common.errors import NorthstarError


class ContractValidationError(NorthstarError):
    """An effect or parameter failed deterministic validation."""

    code = "CONTRACT_INVALID"


class UntraceableAmountError(ContractValidationError):
    """An amount reaches the contract from nowhere the operator said."""

    code = "UNTRACEABLE_AMOUNT"


def validate_effect_name(name: str):
    """Resolve a registry entry (unknown names raise, never improvise)."""
    if not name:
        raise ContractValidationError("empty effect name")
    try:
        return get_effect(name)
    except UnknownEffectError as exc:
        raise ContractValidationError(str(exc)) from None


def validate_effect_params(effect_name: str, params: dict) -> dict:
    """Validate bound parameters against the registry expected-schema."""
    definition = validate_effect_name(effect_name)
    try:
        validated = definition.expected_schema.model_validate(params)
    except ValidationError as exc:
        raise ContractValidationError(f"invalid params for {effect_name}: {exc.errors()}") from None
    return validated.model_dump()


def validate_amount_traceable(amount_paise: int, allowed_paise: list[int]) -> None:
    """An amount must equal one the operator stated (paise ints).

    Ticket/page text never justifies an amount — only the operator task
    (parsed by the service) may. Anything else is rejected here, before
    policy or tools ever see it.
    """
    if amount_paise <= 0:
        raise UntraceableAmountError(f"non-positive amount: {amount_paise}")
    if amount_paise not in allowed_paise:
        raise UntraceableAmountError(f"amount {amount_paise} paise traces to no operator statement")
