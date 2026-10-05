"""Phase 21 red team: false-success states must never verify.

Each red-team case is a corrupted after-state a buggy or lying worker
could leave behind (banner with no row, wrong linkage, duplicates,
touched neighbors). The contract is fixed; only the state varies, so a
VERIFIED here is a false pass. Target false-pass rate: 0.
"""

from verifier.service import verify_contract

CUST, ORDER, ITEM, TICKET = "c1", "o1", "i1", "t1"


def _snap(**collections):
    base = {
        "customers": [{"id": CUST}],
        "orders": [{"id": ORDER, "customer_id": CUST, "status": "delivered", "paid_paise": 50000}],
        "order_items": [{"id": ITEM, "order_id": ORDER}],
        "tickets": [{"id": TICKET, "customer_id": CUST, "status": "open", "version": 1}],
        "ticket_notes": [],
        "refunds": [],
        "replacements": [],
    }
    base.update(collections)
    base["counts"] = {k: len(v) for k, v in base.items() if k != "counts"}
    return base


def _contract(*effects):
    return {
        "customer_id": CUST,
        "order_id": ORDER,
        "ticket_id": TICKET,
        "effects": list(effects),
        "snapshot_scope": {
            "customer_ids": [CUST],
            "order_ids": [ORDER],
            "ticket_ids": [TICKET],
        },
    }


def _replacement_effect():
    return {
        "effect": "replacement.create",
        "params": {"order_id": ORDER, "order_item_id": ITEM, "ticket_id": TICKET},
        "capability": "replacement.create",
    }


def _refund_effect(amount=25000):
    return {
        "effect": "refund.create",
        "params": {"order_id": ORDER, "ticket_id": TICKET, "amount_paise": amount},
        "capability": "refund.create",
    }


def _note_effect(kind="internal", body="handling now"):
    name = "ticket.note" if kind == "internal" else "ticket.reply"
    return {
        "effect": name,
        "params": {"ticket_id": TICKET, "kind": kind, "body": body},
        "capability": "ticket.note" if kind == "internal" else "ticket.reply",
    }


def _status_effect(to="resolved"):
    return {
        "effect": "ticket.status",
        "params": {"ticket_id": TICKET, "to_status": to},
        "capability": "ticket.status",
    }


def _replacement_row(**over):
    row = {
        "id": "r1",
        "order_id": ORDER,
        "order_item_id": ITEM,
        "customer_id": CUST,
        "ticket_id": TICKET,
        "status": "pending",
        "mutation_key": "k1",
    }
    row.update(over)
    return row


def _refund_row(**over):
    row = {
        "id": "f1",
        "order_id": ORDER,
        "customer_id": CUST,
        "ticket_id": TICKET,
        "amount_paise": 25000,
        "status": "pending",
        "mutation_key": "k2",
    }
    row.update(over)
    return row


def _note_row(**over):
    row = {
        "id": "n1",
        "ticket_id": TICKET,
        "kind": "internal",
        "body": "handling now",
        "author": "ops",
        "mutation_key": "k3",
    }
    row.update(over)
    return row


def _verdict(contract, before, after):
    return verify_contract(contract, before, after)["verdict"]


# Correct states verify.


def test_correct_replacement_verifies():
    before = _snap()
    after = _snap(replacements=[_replacement_row()])
    assert _verdict(_contract(_replacement_effect()), before, after) == "verified"


def test_correct_refund_verifies():
    before = _snap()
    after = _snap(refunds=[_refund_row()])
    assert _verdict(_contract(_refund_effect()), before, after) == "verified"


def test_correct_note_and_status_verify():
    before = _snap()
    after = _snap(
        ticket_notes=[_note_row()],
        tickets=[{"id": TICKET, "customer_id": CUST, "status": "resolved", "version": 2}],
    )
    contract = _contract(_note_effect(), _status_effect())
    assert _verdict(contract, before, after) == "verified"


# Red team: none of these may verify.


def test_red_success_banner_with_no_row():
    """No state moved at all (a banner is not proof)."""
    before = _snap()
    assert _verdict(_contract(_replacement_effect()), before, _snap()) == "failed"


def test_red_replacement_wrong_customer():
    before = _snap()
    after = _snap(replacements=[_replacement_row(customer_id="cX")])
    assert _verdict(_contract(_replacement_effect()), before, after) == "failed"


def test_red_replacement_wrong_order():
    before = _snap()
    after = _snap(replacements=[_replacement_row(order_id="oX")])
    assert _verdict(_contract(_replacement_effect()), before, after) == "failed"


def test_red_refund_wrong_amount():
    before = _snap()
    after = _snap(refunds=[_refund_row(amount_paise=99999)])
    assert _verdict(_contract(_refund_effect()), before, after) == "failed"


def test_red_duplicate_replacements():
    before = _snap()
    after = _snap(replacements=[_replacement_row(id="r1"), _replacement_row(id="r2")])
    assert _verdict(_contract(_replacement_effect()), before, after) == "failed"


def test_red_unrelated_order_added():
    """A neighbor order appears: outside the allowed-effects set."""
    before = _snap()
    after = _snap(
        replacements=[_replacement_row()],
        orders=[
            {"id": ORDER, "customer_id": CUST, "status": "delivered", "paid_paise": 50000},
            {"id": "oX", "customer_id": "cX", "status": "placed", "paid_paise": 10},
        ],
    )
    assert _verdict(_contract(_replacement_effect()), before, after) == "failed"


def test_red_ticket_status_not_moved():
    before = _snap()
    assert _verdict(_contract(_status_effect()), before, _snap()) == "failed"


def test_red_note_without_mutation_key():
    before = _snap()
    after = _snap(ticket_notes=[_note_row(mutation_key=None)])
    assert _verdict(_contract(_note_effect()), before, after) == "failed"


def test_red_refund_exceeds_paid():
    before = _snap()
    after = _snap(refunds=[_refund_row(amount_paise=60000)])
    contract = _contract(_refund_effect(amount=60000))
    assert _verdict(contract, before, after) == "failed"


def test_red_row_removed():
    before = _snap(ticket_notes=[_note_row()])
    assert _verdict(_contract(_note_effect()), before, _snap()) == "failed"


# Missing data is inconclusive, never a guess.


def test_missing_before_snapshot_is_inconclusive():
    after = _snap(replacements=[_replacement_row()])
    outcome = verify_contract(_contract(_replacement_effect()), None, after)
    assert outcome["verdict"] == "inconclusive"


def test_unknown_effect_fails_closed():
    before = _snap()
    contract = _contract({"effect": "refund.double", "params": {}, "capability": "refund.create"})
    assert _verdict(contract, before, _snap()) == "failed"
