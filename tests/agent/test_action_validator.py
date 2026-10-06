"""Action validator: rejection and acceptance cases (Phase 14).

Bad tools, out-of-scope capabilities, and wrong bindings fail with
correctable errors; contract-bound proposals for tests A–C pass — the
definition of done for this phase.
"""

from agent.contract.action_validator import TOOL_META, validate_action
from agent.contract.models import Contract, ExpectedEffect


def _contract(**overrides):
    base = {
        "task_id": "t1",
        "goal": "replace the item",
        "customer_id": "c-101",
        "order_id": "o-1942",
        "ticket_id": "t-101",
        "effects": [
            ExpectedEffect(
                effect="replacement.create",
                params={"order_id": "o-1942", "order_item_id": "i-1", "ticket_id": "t-101"},
                capability="replacement.create",
            )
        ],
        "capabilities": ["read", "read.fallback", "probe", "browser", "replacement.create"],
        "ambiguity": [],
        "status": "ok",
    }
    base.update(overrides)
    return Contract.model_validate(base)


def test_unknown_tool_rejected():
    """Hallucinated tools fail closed with a correctable error."""
    outcome = validate_action(
        {"tool": "delete_everything", "params": {}, "rationale": "evil"}, _contract()
    )
    assert not outcome.valid
    assert any("unknown tool" in err for err in outcome.errors)


def test_missing_required_params_rejected():
    """Param-less reads fail validation (correction loop, not dispatch)."""
    outcome = validate_action(
        {"tool": "get_order", "params": {}, "rationale": "look"},
        _contract(),
    )
    assert not outcome.valid
    assert any("order_id" in err for err in outcome.errors)


def test_bound_read_passes():
    """Fully-bound reads validate (the live loop's bread and butter)."""
    outcome = validate_action(
        {"tool": "get_order", "params": {"order_id": "o-1942"}, "rationale": "look"},
        _contract(),
    )
    assert outcome.valid


def test_out_of_scope_capability_rejected():
    """A replacement-scoped task cannot submit a refund form."""
    outcome = validate_action(
        {
            "tool": "browser_submit",
            "params": {"effect": "refund.create", "ref": "e3", "order_id": "o-1942"},
            "rationale": "wrong form",
        },
        _contract(),
    )
    assert not outcome.valid
    assert any("capability" in err for err in outcome.errors)


def test_browser_needs_browser_capability():
    """Reads without their capability fail (ungranted task)."""
    outcome = validate_action(
        {"tool": "browser_open", "params": {}, "rationale": " surf"},
        _contract(capabilities=["read"]),
    )
    assert not outcome.valid
    assert any("browser" in err for err in outcome.errors)


def test_wrong_order_id_rejected():
    """Bindings must equal the locked contract, not resemble it."""
    outcome = validate_action(
        {
            "tool": "browser_submit",
            "params": {
                "effect": "replacement.create",
                "ref": "e7",
                "order_id": "o-9999",
                "order_item_id": "i-1",
                "ticket_id": "t-101",
            },
            "rationale": "wrong order",
        },
        _contract(),
    )
    assert not outcome.valid
    assert any("binding" in err for err in outcome.errors)


def test_wrong_amount_rejected():
    """Refund amounts must equal the contracted paise exactly."""
    contract = _contract(
        effects=[
            ExpectedEffect(
                effect="refund.create",
                params={"order_id": "o-1942", "ticket_id": "t-101", "amount_paise": 250000},
                capability="refund.create",
            )
        ],
        capabilities=["read", "read.fallback", "probe", "browser", "refund.create"],
    )
    outcome = validate_action(
        {
            "tool": "browser_submit",
            "params": {
                "effect": "refund.create",
                "ref": "e9",
                "order_id": "o-1942",
                "ticket_id": "t-101",
                "amount_paise": 3500000,
            },
            "rationale": "wrong amount",
        },
        contract,
    )
    assert not outcome.valid
    assert any("binding" in err for err in outcome.errors)


def test_bad_ref_rejected():
    """Refs come from observations (`e12`), never from the model."""
    outcome = validate_action(
        {"tool": "browser_click", "params": {"ref": "submit-button"}, "rationale": "x"},
        _contract(),
    )
    assert not outcome.valid


def test_malformed_action_rejected():
    """Schema garbage fails before any semantic check runs."""
    outcome = validate_action({"tool": "get_order"}, _contract())
    assert not outcome.valid
    assert any("schema" in err for err in outcome.errors)


def test_missing_params_name_missing_and_received():
    """Multi-param errors name both sides so corrections merge, not swap."""
    outcome = validate_action(
        {"tool": "inspect_state", "params": {"kind": "refund"}, "rationale": "probe"},
        _contract(),
    )
    assert not outcome.valid
    assert outcome.errors == ["params: inspect_state needs ['key'] together (got ['kind'])"]


def test_valid_read_passes():
    """Contract-bound reads flow to policy."""
    outcome = validate_action(
        {"tool": "search_order", "params": {"customer_id": "c-101"}, "rationale": "find"},
        _contract(),
    )
    assert outcome.valid


def test_valid_submit_passes():
    """Exact binding match commits past the validator (policy decides)."""
    outcome = validate_action(
        {
            "tool": "browser_submit",
            "params": {
                "effect": "replacement.create",
                "ref": "e7",
                "mutation_key": "k1",
                "order_id": "o-1942",
                "order_item_id": "i-1",
                "ticket_id": "t-101",
            },
            "rationale": "do it",
        },
        _contract(),
    )
    assert outcome.valid


def test_validated_actions_for_core_scenarios():
    """Definition of done: only validated actions reach tests A–C."""

    def refund_contract(amount):
        return _contract(
            effects=[
                ExpectedEffect(
                    effect="refund.create",
                    params={
                        "order_id": "o-1942",
                        "ticket_id": "t-101",
                        "amount_paise": amount,
                    },
                    capability="refund.create",
                )
            ],
            capabilities=["read", "read.fallback", "probe", "browser", "refund.create"],
        )

    submit = {
        "tool": "browser_submit",
        "params": {
            "effect": "refund.create",
            "ref": "e5",
            "order_id": "o-1942",
            "ticket_id": "t-101",
            "amount_paise": 250000,
        },
        "rationale": "test B",
    }
    assert validate_action(submit, refund_contract(250000)).valid
    assert not validate_action(submit, refund_contract(3500000)).valid


def test_tool_mirror_matches_registry():
    """The agent mirror names every MCP tool (drift fails the build)."""
    from mcp_server.registry import TOOL_NAMES

    assert set(TOOL_META) == set(TOOL_NAMES)
    assert TOOL_META["browser_submit"].kind == "write"
    assert all(meta.kind == "read" for name, meta in TOOL_META.items() if name != "browser_submit")
