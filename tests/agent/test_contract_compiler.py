"""Contract compiler: deterministic mapping to ok/ambiguous/unsupported.

Pure tests (no gateway, no LLM, no database): the interpretation and
resolution are constructed by hand, so every branch of the outcome rules
is pinned.
"""

import pytest

from agent.contract.compiler import compile_contract, snapshot_scope
from agent.contract.models import EntityResolution
from agent.contract.validators import (
    ContractValidationError,
    UntraceableAmountError,
    validate_amount_traceable,
    validate_effect_name,
    validate_effect_params,
)
from agent.llm.schemas import Interpretation

TASK = "t-test"


def _interpretation(**overrides):
    base = {
        "summary": "summary",
        "goal": "goal",
        "requested_effects": [],
        "mentioned_codes": [],
        "mentioned_names": [],
        "ambiguities": [],
        "unsupported": False,
    }
    base.update(overrides)
    return Interpretation.model_validate(base)


def _resolution(**overrides):
    base = {
        "customer": {"id": "c-101", "code": "C101", "name": "Arjun"},
        "order": {
            "id": "o-1942",
            "code": "ORD-1942",
            "customer_id": "c-101",
            "items": [{"id": "i-1", "title": "ProBook Laptop 14", "sku": "LAP-X1"}],
        },
        "ticket": {
            "id": "t-101",
            "code": "TCK-101",
            "customer_id": "c-101",
            "order_id": "o-1942",
        },
        "ambiguities": [],
        "unmatched_codes": [],
    }
    base.update(overrides)
    return EntityResolution.model_validate(base)


def test_replacement_compiles_ok():
    """Test A at contract level: bound IDs, validated params, scoped caps."""
    contract = compile_contract(
        TASK,
        "Replace the damaged ProBook laptop on order ORD-1942 (ticket TCK-101).",
        _interpretation(requested_effects=["replacement.create"]),
        _resolution(),
        [],
    )
    assert contract.status == "ok"
    assert contract.order_id == "o-1942" and contract.ticket_id == "t-101"
    [effect] = contract.effects
    assert effect.effect == "replacement.create"
    assert effect.params["order_item_id"] == "i-1"
    assert "replacement.create" in contract.capabilities
    assert set(("read", "probe", "browser")) <= set(contract.capabilities)


def test_refund_compiles_with_operator_amount():
    """Tests B/C at contract level: the operator's paise bind the effect."""
    contract = compile_contract(
        TASK,
        "Refund Rs. 2,500 for the faulty headphones.",
        _interpretation(requested_effects=["refund.create"]),
        _resolution(),
        [250000],
    )
    assert contract.status == "ok"
    [effect] = contract.effects
    assert effect.params["amount_paise"] == 250000


def test_unknown_effect_is_unsupported():
    """No effect outside the registry (definition of done)."""
    contract = compile_contract(
        TASK,
        "Apply a 10% coupon to the order.",
        _interpretation(requested_effects=["coupon.apply"]),
        _resolution(),
        [],
    )
    assert contract.status == "unsupported"
    assert contract.effects == []


def test_unsupported_interpretation_is_unsupported():
    """The LLM's own unsupported flag is honored, never overridden."""
    contract = compile_contract(
        TASK,
        "Order a pepperoni pizza.",
        _interpretation(unsupported=True),
        _resolution(),
        [],
    )
    assert contract.status == "unsupported"


def test_cancellation_with_ticket_is_ambiguous():
    """Test D at contract level: cancel scope parks for the operator."""
    contract = compile_contract(
        TASK,
        "Cancel the customer's order (ticket TCK-104 says only 'cancel my order').",
        _interpretation(),
        _resolution(ticket={"id": "t-104", "code": "TCK-104"}),
        [],
    )
    assert contract.status == "ambiguous"
    assert any("scope" in item for item in contract.ambiguity)


def test_unmappable_task_without_ticket_is_unsupported():
    """Test J (negative): no mapping, no ticket — INCONCLUSIVE downstream."""
    contract = compile_contract(
        TASK,
        "Order a pepperoni pizza.",
        _interpretation(),
        _resolution(customer=None, order=None, ticket=None),
        [],
    )
    assert contract.status == "unsupported"


def test_resolution_ambiguity_parks():
    """Look-alikes and ownership conflicts never bind a guess."""
    resolution = _resolution(ambiguities=["multiple customers match 'Priya Nair'"])
    contract = compile_contract(
        TASK, "Help Priya Nair.", _interpretation(requested_effects=["ticket.note"]), resolution, []
    )
    assert contract.status == "ambiguous"
    assert contract.effects == []


def test_unmatched_codes_park():
    """Codes no read can resolve become clarification questions."""
    resolution = _resolution(unmatched_codes=["ORD-9999"])
    contract = compile_contract(
        TASK,
        "Replace on order ORD-9999.",
        _interpretation(requested_effects=["replacement.create"]),
        resolution,
        [],
    )
    assert contract.status == "ambiguous"
    assert any("ORD-9999" in item for item in contract.ambiguity)


def test_refund_without_operator_amount_parks():
    """No amount untraceable to the operator reaches an effect."""
    contract = compile_contract(
        TASK,
        "Refund the ticket.",
        _interpretation(requested_effects=["refund.create"]),
        _resolution(),
        [],
    )
    assert contract.status == "ambiguous"


def test_snapshot_scope_lists_bound_entities():
    """The verifier scope covers exactly the bound triple."""
    contract = compile_contract(
        TASK,
        "Replace.",
        _interpretation(requested_effects=["replacement.create"]),
        _resolution(),
        [],
    )
    assert snapshot_scope(contract) == {
        "customer_ids": ["c-101"],
        "order_ids": ["o-1942"],
        "ticket_ids": ["t-101"],
    }


def test_effect_name_validation():
    """Empty and unknown names raise; registry names resolve."""
    with pytest.raises(ContractValidationError):
        validate_effect_name("")
    with pytest.raises(ContractValidationError):
        validate_effect_name("refund.delete")
    assert validate_effect_name("refund.create").capability == "refund.create"


def test_effect_params_validation():
    """Schema violations fail before any downstream sees the params."""
    with pytest.raises(ContractValidationError):
        validate_effect_params("refund.create", {"order_id": "o", "ticket_id": "t"})
    validated = validate_effect_params(
        "refund.create", {"order_id": "o", "ticket_id": "t", "amount_paise": 100}
    )
    assert validated["amount_paise"] == 100


def test_amount_traceability():
    """Only operator-stated paise pass; ticket figures never do."""
    validate_amount_traceable(250000, [250000])
    with pytest.raises(UntraceableAmountError):
        validate_amount_traceable(10000000, [250000])
    with pytest.raises(UntraceableAmountError):
        validate_amount_traceable(0, [0])


def test_policy_scope_matches_enforced_bindings():
    """policy_scope locks exactly what P-CAP/P-OWN enforce (Phase 15)."""
    interpretation = _interpretation(requested_effects=["replacement.create"])
    contract = compile_contract(
        TASK,
        "Replace the damaged ProBook laptop on order ORD-1942 (ticket TCK-101).",
        interpretation,
        _resolution(),
        [],
    )
    assert contract.status == "ok"
    assert contract.policy_scope == {
        "customer_id": "c-101",
        "order_id": "o-1942",
        "ticket_id": "t-101",
        "capabilities": contract.capabilities,
        "effects": ["replacement.create"],
    }


def test_policy_scope_present_on_parked_contracts():
    """Ambiguous contracts lock scope too (clarification cannot widen it)."""
    interpretation = _interpretation(requested_effects=[], goal="cancel it")
    contract = compile_contract("t-2", "cancel my order", interpretation, _resolution(), [])
    assert contract.status in ("ambiguous", "unsupported")
    assert contract.policy_scope["capabilities"] == contract.capabilities
    assert contract.policy_scope["effects"] == []
