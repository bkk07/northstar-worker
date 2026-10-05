"""Phase 29 consolidation: adversarial attacks on the fixed boundaries.

One file drives every confusion at the two hardened seams — ownership
(triple mismatches in every combination) and the terminal gate (a minor
submit ahead of a major doomed by each rule). Every attack must end in
a deterministic BLOCK with no token and no commit: the attacker never
gets prose, clarification, or a partial mutation.
"""

import datetime

from agent.contract.compiler import compile_contract
from agent.contract.models import Contract, EntityResolution, ExpectedEffect
from agent.llm.schemas import Interpretation
from agent.policy import authorization
from agent.policy.facts import Facts

TODAY = datetime.date(2026, 10, 4)


def _interpretation(*effects):
    return Interpretation.model_validate(
        {
            "summary": "s",
            "goal": "g",
            "requested_effects": list(effects),
            "mentioned_codes": [],
            "mentioned_names": [],
            "ambiguities": [],
            "unsupported": False,
        }
    )


def _resolution(customer="c-101", order_customer="c-101", ticket_customer="c-101"):
    mismatched = len({customer, order_customer, ticket_customer}) > 1
    return EntityResolution.model_validate(
        {
            "customer": {"id": customer, "code": "C1", "name": "A"},
            "order": {
                "id": "o-1",
                "code": "ORD-1",
                "customer_id": order_customer,
                "items": [{"id": "i-1", "title": "T", "sku": "S"}],
            },
            "ticket": {
                "id": "t-1",
                "code": "TCK-1",
                "customer_id": ticket_customer,
                "order_id": "o-1",
            },
            # `_cross_check_ownership` (contract service) writes these;
            # the compiler partitions them into a recorded ok-contract.
            "ambiguities": (["ownership mismatch: bound triple disagrees"] if mismatched else []),
            "unmatched_codes": [],
        }
    )


def _order(days_ago=5, paid=8500000, category="electronics"):
    return {
        "id": "o-1",
        "code": "ORD-1",
        "customer_id": "c-101",
        "status": "delivered",
        "total_paise": paid,
        "paid_paise": paid,
        "delivered_at": (TODAY - datetime.timedelta(days=days_ago)).isoformat(),
        "items": [
            {
                "id": "i-1",
                "title": "T",
                "sku": "S",
                "qty": 1,
                "unit_paise": 8500000,
                "category": category,
            }
        ],
    }


def _ticket(customer="c-101"):
    return {
        "id": "t-1",
        "code": "TCK-1",
        "customer_id": customer,
        "order_id": "o-1",
        "category": "damage",
        "status": "open",
    }


def _facts(**overrides):
    base = {
        "customer_id": "c-101",
        "order": _order(),
        "ticket": _ticket(),
        "customer": {"id": "c-101"},
    }
    base.update(overrides)
    return Facts(**base)


def _contract(*effects):
    return Contract(
        task_id="t1",
        goal="g",
        customer_id="c-101",
        order_id="o-1",
        ticket_id="t-1",
        effects=list(effects),
        capabilities=["read", "read.fallback", "probe", "browser"]
        + sorted({e.capability for e in effects}),
        status="ok",
    )


def _major(kind, **params):
    if kind == "refund":
        return ExpectedEffect(
            effect="refund.create",
            params={"order_id": "o-1", "ticket_id": "t-1", **params},
            capability="refund.create",
        )
    return ExpectedEffect(
        effect="replacement.create",
        params={"order_id": "o-1", "order_item_id": "i-1", "ticket_id": "t-1"},
        capability="replacement.create",
    )


def _note():
    return ExpectedEffect(
        effect="ticket.note",
        params={"ticket_id": "t-1", "kind": "internal", "body": "hi"},
        capability="ticket.note",
    )


def _note_action():
    return {
        "tool": "browser_submit",
        "params": {
            "effect": "ticket.note",
            "ref": "x",
            "ticket_id": "t-1",
            "kind": "internal",
            "body": "hi",
        },
    }


def _terminal_block(contract, facts):
    """The gate verdict for the held note (node path, without servers)."""
    from agent.services.policy_service import MAJOR_EFFECTS, MINOR_EFFECTS

    assert "ticket.note" in MINOR_EFFECTS and "refund.create" in MAJOR_EFFECTS
    gate_major = next(e for e in contract.effects if e.effect in MAJOR_EFFECTS)
    prospect = {
        "tool": "browser_submit",
        "params": {"effect": gate_major.effect, **dict(gate_major.params)},
    }
    return authorization.evaluate(contract, prospect, facts, TODAY)


def test_ownership_confusions_compile_for_block():
    """Every triple mismatch compiles ok — never a clarification."""
    cases = [
        _resolution(customer="c-101", order_customer="c-102", ticket_customer="c-101"),
        _resolution(customer="c-101", order_customer="c-101", ticket_customer="c-102"),
        _resolution(customer="c-101", order_customer="c-102", ticket_customer="c-103"),
    ]
    for resolution in cases:
        contract = compile_contract(
            "t", "Replace it.", _interpretation("replacement.create"), resolution, []
        )
        assert contract.status == "ok", resolution
        assert contract.traceability["ownership_conflict"]

    consistent = _resolution(customer="c-102", order_customer="c-102", ticket_customer="c-102")
    clean = compile_contract(
        "t", "Replace it.", _interpretation("replacement.create"), consistent, []
    )
    assert clean.status == "ok"
    assert "ownership_conflict" not in clean.traceability


def test_all_doomed_majors_hold_the_note():
    """Each BLOCK rule fires prospectively: cap, ownership, dup, window, category."""
    over_cap = _contract(_major("refund", amount_paise=8000000), _note())
    assert _terminal_block(over_cap, _facts()).rule_id == "P-REF-004"

    foreign = _contract(_major("refund", amount_paise=100), _note())
    assert _terminal_block(foreign, _facts(ticket=_ticket(customer="c-102"))).rule_id == "P-OWN-001"

    dupe = _contract(_major("refund", amount_paise=100), _note())
    assert (
        _terminal_block(dupe, _facts(existing_refund={"found": True, "kind": "refund"})).rule_id
        == "P-DUP-001"
    )

    stale = _contract(_major("replacement"), _note())
    assert _terminal_block(stale, _facts(order=_order(days_ago=45))).rule_id == "E-REPL-001"

    final_sale = _contract(_major("refund", amount_paise=100), _note())
    assert (
        _terminal_block(final_sale, _facts(order=_order(category="final_sale"))).rule_id
        == "E-REF-002"
    )


def test_healthy_and_approval_majors_release_the_note():
    """ALLOW and HUMAN_APPROVAL majors never hold a note."""
    auto = _contract(_major("refund", amount_paise=100), _note())
    assert _terminal_block(auto, _facts()).outcome in ("allow", "human_approval")

    approval = _contract(_major("refund", amount_paise=3500000), _note())
    assert _terminal_block(approval, _facts()).outcome == "human_approval"

    replacement = _contract(_major("replacement"), _note())
    assert _terminal_block(replacement, _facts()).outcome == "allow"


def test_injection_amounts_stay_out_of_effects():
    """A ticket screaming a payout binds nothing: amounts are operator-only."""
    resolution = _resolution()
    contract = compile_contract(
        "t",
        "Process the payout.",
        _interpretation("refund.create"),
        resolution,
        [],
    )
    assert contract.status == "ambiguous"  # no operator amount: clarify, never invent
    assert contract.effects == []
