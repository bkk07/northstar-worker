"""Authorization table: every rule and boundary (Phase 15).

Pure `evaluate` calls with hand-built facts — no gateway, no database.
Amounts are paise; boundaries pin the exact paise where bands change.
"""

import pytest

from agent.contract.models import Contract, ExpectedEffect
from agent.policy import authorization
from agent.policy.facts import Facts
from tests.policy.conftest import TODAY, order, ticket


def _contract(*effects, caps=None, customer="c-101", order_id="o-1942", ticket="t-101"):
    return Contract(
        task_id="t1",
        goal="goal",
        customer_id=customer,
        order_id=order_id,
        ticket_id=ticket,
        effects=list(effects),
        capabilities=caps
        if caps is not None
        else ["read", "read.fallback", "probe", "browser"]
        + sorted({e.capability for e in effects}),
        status="ok",
    )


def _replacement_effect():
    return ExpectedEffect(
        effect="replacement.create",
        params={"order_id": "o-1942", "order_item_id": "i-1", "ticket_id": "t-101"},
        capability="replacement.create",
    )


def _refund_effect(amount):
    return ExpectedEffect(
        effect="refund.create",
        params={"order_id": "o-1942", "ticket_id": "t-101", "amount_paise": amount},
        capability="refund.create",
    )


def _submit(effect, **params):
    return {
        "tool": "browser_submit",
        "params": {"effect": effect, "ref": "e1", **params},
        "rationale": "test",
    }


def _facts(**overrides):
    base = {
        "customer_id": "c-101",
        "order": order(),
        "ticket": ticket(),
        "customer": {"id": "c-101"},
    }
    base.update(overrides)
    return Facts(**base)


def decide(contract, action, facts):
    """Evaluate on the pinned test date."""
    return authorization.evaluate(contract, action, facts, TODAY)


def test_unknown_tool_blocked():
    """Unknown actions fail closed (P-FAIL-CLOSED)."""
    result = decide(_contract(), {"tool": "teleport", "params": {}}, _facts())
    assert (result.outcome, result.rule_id) == ("block", "P-FAIL-CLOSED")


def test_out_of_scope_effect_blocked():
    """Commits outside the contract never reach effect rules."""
    contract = _contract(_replacement_effect())
    result = decide(contract, _submit("refund.create", amount_paise=100), _facts())
    assert (result.outcome, result.rule_id) == ("block", "P-CAP-001")


def test_read_without_capability_blocked():
    """Capability denial is deterministic, not advisory."""
    contract = _contract(_replacement_effect(), caps=["read"])
    action = {"tool": "browser_open", "params": {}, "rationale": "x"}
    result = decide(contract, action, _facts())
    assert (result.outcome, result.rule_id) == ("block", "P-CAP-001")


def test_in_scope_read_allowed():
    """Reads inside scope ALLOW on the scope rule itself."""
    contract = _contract()
    action = {"tool": "search_order", "params": {"customer_id": "c-101"}, "rationale": "x"}
    result = decide(contract, action, _facts())
    assert (result.outcome, result.rule_id) == ("allow", "P-CAP-001")


def test_ownership_mismatch_blocked():
    """Cross-customer triples BLOCK even when each read exists."""
    contract = _contract(_replacement_effect())
    facts = _facts(ticket=ticket(customer="c-102"))
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("block", "P-OWN-001")


def test_duplicate_replacement_blocked():
    """Active replacements reconcile, never duplicate."""
    contract = _contract(_replacement_effect())
    facts = _facts(existing_replacement={"found": True, "kind": "replacement"})
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("block", "P-DUP-001")


def test_duplicate_refund_blocked():
    """Active refunds reconcile, never duplicate."""
    contract = _contract(_refund_effect(250000))
    facts = _facts(existing_refund={"found": True, "kind": "refund"})
    action = _submit("refund.create", order_id="o-1942", ticket_id="t-101", amount_paise=250000)
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("block", "P-DUP-001")


def test_same_amount_new_ticket_blocked():
    """The 'again' trap: same order + amount on another ticket BLOCKs."""
    contract = _contract(_refund_effect(90000))
    action = _submit("refund.create", order_id="o-1942", ticket_id="t-139", amount_paise=90000)
    facts = _facts(
        order_refunds=[{"ticket_id": "t-H4", "order_id": "o-1942", "amount_paise": 90000}],
        refunds_last_90d=4,
    )
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("block", "P-DUP-001")


def test_different_amount_new_ticket_passes_dup():
    """Genuine top-ups are not duplicates (amount bands still apply)."""
    contract = _contract(_refund_effect(50000))
    action = _submit("refund.create", order_id="o-1942", ticket_id="t-139", amount_paise=50000)
    facts = _facts(
        order=order(paid=9000000),
        order_refunds=[{"ticket_id": "t-H4", "order_id": "o-1942", "amount_paise": 90000}],
    )
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("allow", "P-REF-001")


def test_defect_hints_report_damage():
    """Stuck zippers and open seams count as reported damage."""
    contract = _contract(_replacement_effect())
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    for subject, body in [
        ("Jacket arrived late", "The zipper is stuck. Replace it."),
        ("Dress stitching", "A seam is open. Please replace it."),
    ]:
        facts = _facts(ticket=ticket(category="late_delivery"))
        facts.ticket["subject"] = subject
        facts.ticket["body"] = body
        result = decide(contract, action, facts)
        assert result.outcome == "allow", (subject, result)


def test_eligible_replacement_allowed():
    """In-window damaged delivery ALLOWs on P-REPL-001."""
    contract = _contract(_replacement_effect())
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    result = decide(contract, action, _facts())
    assert (result.outcome, result.rule_id) == ("allow", "P-REPL-001")


def test_expensive_replacement_needs_approval():
    """Above Rs. 1,50,000 the same facts route to HUMAN_APPROVAL."""
    big = order(
        paid=20000000,
        items=[
            {
                "id": "i-9",
                "title": "X",
                "sku": "X",
                "qty": 1,
                "unit_paise": 20000000,
                "category": "electronics",
            }
        ],
    )
    effect = ExpectedEffect(
        effect="replacement.create",
        params={"order_id": "o-1942", "order_item_id": "i-9", "ticket_id": "t-101"},
        capability="replacement.create",
    )
    contract = _contract(effect)
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-9", ticket_id="t-101"
    )
    result = decide(contract, action, _facts(order=big))
    assert (result.outcome, result.rule_id) == ("human_approval", "P-REPL-002")


@pytest.mark.parametrize("days_ago", [30, 31])
def test_replacement_window_boundary(days_ago):
    """Day 30 is eligible; day 31 is not (E-REPL-001)."""
    contract = _contract(_replacement_effect())
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    result = decide(contract, action, _facts(order=order(days_ago=days_ago)))
    if days_ago <= 30:
        assert result.outcome == "allow"
    else:
        assert (result.outcome, result.rule_id) == ("block", "E-REPL-001")


def test_undelivered_order_ineligible():
    """Open orders cannot draw replacements."""
    contract = _contract(_replacement_effect())
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    result = decide(contract, action, _facts(order=order(status="open")))
    assert (result.outcome, result.rule_id) == ("block", "E-REPL-001")


def test_no_damage_report_ineligible():
    """Clean tickets cannot draw damage replacements."""
    contract = _contract(_replacement_effect())
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    facts = _facts(ticket=ticket(category="general"))
    facts.ticket["subject"] = "Question"
    facts.ticket["body"] = "Just asking."
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("block", "E-REPL-001")


@pytest.mark.parametrize(
    ("amount", "count", "outcome", "rule"),
    [
        (250000, 0, "allow", "P-REF-001"),  # test B band
        (500000, 2, "allow", "P-REF-001"),  # exact cap, exact count
        (500001, 0, "human_approval", "P-REF-003"),  # one paise over
        (3500000, 0, "human_approval", "P-REF-003"),  # test C band
        (5000000, 0, "human_approval", "P-REF-003"),  # approval cap itself
        (5000001, 0, "block", "P-REF-004"),  # one paise over the cap
        (100000, 3, "allow", "P-REF-002"),  # repeat, tiny band
        (100001, 3, "human_approval", "P-REF-002"),  # repeat, over tiny
        (600000, 5, "human_approval", "P-REF-002"),  # repeat, never P-REF-001
        (400000, 2, "allow", "P-REF-001"),  # two priors is not repeat
    ],
)
def test_refund_bands_and_boundaries(amount, count, outcome, rule):
    """Every refund band and its exact paise/count edges."""
    contract = _contract(_refund_effect(amount))
    action = _submit("refund.create", order_id="o-1942", ticket_id="t-101", amount_paise=amount)
    facts = _facts(order=order(paid=9000000), refunds_last_90d=count)
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == (outcome, rule)


def test_refund_above_paid_blocked():
    """Refunds above paid BLOCK on P-REF-004 (never approve debt)."""
    contract = _contract(_refund_effect(300000))
    action = _submit("refund.create", order_id="o-1942", ticket_id="t-101", amount_paise=300000)
    result = decide(contract, action, _facts(order=order(paid=250000)))
    assert (result.outcome, result.rule_id) == ("block", "P-REF-004")


def test_non_refundable_category_blocked():
    """Final-sale items BLOCK on E-REF-002."""
    items = [
        {
            "id": "i-1",
            "title": "X",
            "sku": "X",
            "qty": 1,
            "unit_paise": 100,
            "category": "final_sale",
        }
    ]
    contract = _contract(_refund_effect(100))
    action = _submit("refund.create", order_id="o-1942", ticket_id="t-101", amount_paise=100)
    facts = _facts(order=order(paid=100, items=items))
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("block", "E-REF-002")


def test_note_on_own_ticket_allowed():
    """Notes, replies, and status on the contract ticket ALLOW."""
    effect = ExpectedEffect(
        effect="ticket.note",
        params={"ticket_id": "t-101", "kind": "internal", "body": "hi"},
        capability="ticket.note",
    )
    contract = _contract(effect)
    action = {
        "tool": "browser_submit",
        "params": {
            "effect": "ticket.note",
            "ref": "e2",
            "ticket_id": "t-101",
            "kind": "internal",
            "body": "hi",
        },
        "rationale": "x",
    }
    result = decide(contract, action, _facts())
    assert (result.outcome, result.rule_id) == ("allow", "P-NOTE-001")


def test_note_on_other_ticket_blocked():
    """Notes outside the contract ticket are out of scope."""
    effect = ExpectedEffect(
        effect="ticket.note",
        params={"ticket_id": "t-101", "kind": "internal", "body": "hi"},
        capability="ticket.note",
    )
    contract = _contract(effect)
    action = {
        "tool": "browser_submit",
        "params": {
            "effect": "ticket.note",
            "ref": "e2",
            "ticket_id": "t-999",
            "kind": "internal",
            "body": "hi",
        },
        "rationale": "x",
    }
    result = decide(contract, action, _facts())
    assert (result.outcome, result.rule_id) == ("block", "P-CAP-001")


def test_missing_facts_blocked():
    """Commits without order facts fail closed, never assumed."""
    contract = _contract(_replacement_effect())
    action = _submit(
        "replacement.create", order_id="o-1942", order_item_id="i-1", ticket_id="t-101"
    )
    facts = _facts(order={}, missing=["order"])
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("block", "P-FAIL-CLOSED")


def test_thresholds_are_parameter_aware():
    """Seeded policy rows move the bands (nothing hardcoded)."""
    contract = _contract(_refund_effect(250000))
    action = _submit("refund.create", order_id="o-1942", ticket_id="t-101", amount_paise=250000)
    facts = _facts(policies={"P-REF-001": {"max_paise": 100, "max_count_90d": 2}})
    result = decide(contract, action, facts)
    assert (result.outcome, result.rule_id) == ("human_approval", "P-REF-003")
