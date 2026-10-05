"""Contract service: catalog scenarios at contract level (Phase 13).

Fake gateway + fake understanding, real compiler, real persistence on
live Postgres. Covers tests A–D, H, and J at the contract boundary:
what the graph routes on before policy, tools, or the verifier exist.
"""

import uuid

import pytest

from agent.llm.schemas import Interpretation
from agent.services.contract_service import (
    ContractService,
    extract_codes,
    parse_operator_amounts,
    resolve_entities,
)
from database import session as session_factory
from database.models.worker.task import Task, TaskContract

WORLD = {
    "customers": [
        {"id": "c-101", "code": "C101", "name": "Arjun Mehta"},
        {"id": "c-102", "code": "C102", "name": "Divya Rao"},
        {"id": "c-104", "code": "C104", "name": "Kiran Shah"},
        {"id": "c-105", "code": "C105", "name": "Priya Nair"},
        {"id": "c-106", "code": "C106", "name": "Priya Nayar"},
        {"id": "c-109", "code": "C109", "name": "Meera Iyer"},
    ],
    "orders": {
        "ORD-1942": {
            "id": "o-1942",
            "code": "ORD-1942",
            "customer_id": "c-101",
            "items": [{"id": "i-1", "title": "ProBook Laptop 14", "sku": "LAP-X1"}],
        },
        "ORD-1943": {
            "id": "o-1943",
            "code": "ORD-1943",
            "customer_id": "c-102",
            "items": [{"id": "i-2", "title": "Studio Headphones", "sku": "HP-01"}],
        },
        "ORD-1944": {
            "id": "o-1944",
            "code": "ORD-1944",
            "customer_id": "c-109",
            "items": [{"id": "i-3", "title": "55in QLED TV", "sku": "TV-55"}],
        },
    },
    "tickets": {
        "TCK-101": {"id": "t-101", "code": "TCK-101", "customer_id": "c-101", "order_id": "o-1942"},
        "TCK-102": {"id": "t-102", "code": "TCK-102", "customer_id": "c-102", "order_id": "o-1943"},
        "TCK-103": {"id": "t-103", "code": "TCK-103", "customer_id": "c-109", "order_id": "o-1944"},
        "TCK-104": {"id": "t-104", "code": "TCK-104", "customer_id": "c-104", "order_id": ""},
        "TCK-105": {"id": "t-105", "code": "TCK-105", "customer_id": "c-999", "order_id": "o-1943"},
        "TCK-140": {"id": "t-140", "code": "TCK-140", "customer_id": "c-101", "order_id": "o-1942"},
    },
}


class FakeGateway:
    """Canned read tools over the WORLD above (no backend needed)."""

    def search_customer(self, task_id, q):
        """Code-exact or trigram-like name matches (look-alikes included)."""
        if q in {c["code"] for c in WORLD["customers"]}:
            return {"customers": [c for c in WORLD["customers"] if c["code"] == q]}
        token = q.split()[0].lower() if q.split() else ""
        return {
            "customers": [c for c in WORLD["customers"] if token and token in c["name"].lower()]
        }

    def get_customer(self, task_id, customer_id):
        """One customer by id (missing raises like the real client)."""
        for customer in WORLD["customers"]:
            if customer["id"] == customer_id:
                return {"customer": customer}
        raise RuntimeError("not_found: customer")

    def api_get(self, task_id, path, params=None):
        """Code-addressable shop reads (missing raises like the client)."""
        if path.startswith("/api/shop/orders/"):
            order = WORLD["orders"].get(path.rsplit("/", 1)[-1])
        elif path.startswith("/api/shop/tickets/"):
            order = WORLD["tickets"].get(path.rsplit("/", 1)[-1])
        else:
            raise RuntimeError(f"rejected: {path}")
        if not order:
            raise RuntimeError("not_found")
        return {"result": order}

    def get_order(self, task_id, order_id):
        """One order by id (missing raises like the real client)."""
        for order in WORLD["orders"].values():
            if order["id"] == order_id:
                return {"order": order}
        raise RuntimeError("not_found: order")


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


class _FixedUnderstanding:
    """UnderstandingService double returning one preset proposal."""

    def __init__(self, interpretation):
        self._interpretation = interpretation

    def interpret(self, task_text):
        """Ignore the text; the preset drives the test."""
        _ = task_text
        return self._interpretation


@pytest.fixture()
def task_id():
    """Throwaway worker task row (contract FK target), cleaned up after."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = Task(
        id=uuid.uuid4(),
        text="contract probe",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase13-test",
    )
    session.add(task)
    session.commit()
    key = str(task.id)
    try:
        yield key
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.query(TaskContract).filter(TaskContract.task_id == task.id).delete(
                synchronize_session=False
            )
            cleanup.query(Task).filter(Task.id == task.id).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()
        session.close()


def _service(interpretation):
    sessions = lambda: session_factory.session_for(session_factory.admin_engine())  # noqa: E731
    return ContractService(_FixedUnderstanding(interpretation), FakeGateway(), sessions)


def test_s1_replacement_contract(task_id):
    """Test A: damaged laptop binds replacement.create with DB IDs."""
    service = _service(
        _interpretation(
            summary="Replace the damaged laptop",
            goal="customer has a working laptop",
            requested_effects=["replacement.create"],
            mentioned_codes=["ORD-1942", "TCK-101"],
        )
    )
    contract = service.build_contract(
        task_id, "Replace the damaged ProBook laptop on order ORD-1942 (ticket TCK-101)."
    )
    assert contract.status == "ok"
    assert (contract.customer_id, contract.order_id, contract.ticket_id) == (
        "c-101",
        "o-1942",
        "t-101",
    )
    [effect] = contract.effects
    assert effect.effect == "replacement.create"
    assert effect.params["order_item_id"] == "i-1"


def test_s2_refund_contract(task_id):
    """Test B: operator paise bind the refund amount."""
    service = _service(
        _interpretation(
            goal="refund the headphones",
            requested_effects=["refund.create"],
            mentioned_codes=["ORD-1943", "TCK-102"],
        )
    )
    contract = service.build_contract(
        task_id, "Refund Rs. 2,500 for the faulty headphones on order ORD-1943 (ticket TCK-102)."
    )
    assert contract.status == "ok"
    [effect] = contract.effects
    assert effect.params["amount_paise"] == 250000


def test_s3_large_refund_still_compiles(task_id):
    """Test C: contract is ok; HUMAN_APPROVAL is policy's call (Phase 15)."""
    service = _service(
        _interpretation(
            goal="refund the TV",
            requested_effects=["refund.create"],
            mentioned_codes=["ORD-1944", "TCK-103"],
        )
    )
    contract = service.build_contract(
        task_id, "Refund Rs. 35,000 for the flickering TV on order ORD-1944 (ticket TCK-103)."
    )
    assert contract.status == "ok"
    assert contract.effects[0].params["amount_paise"] == 3500000


def test_s4_ambiguous_cancel_parks(task_id):
    """Test D: bare cancellation clarifies instead of guessing."""
    service = _service(_interpretation(goal="cancel the order"))
    contract = service.build_contract(
        task_id, "Cancel the customer's order (ticket TCK-104 says only 'cancel my order')."
    )
    assert contract.status == "ambiguous"
    assert contract.effects == []


def test_h_look_alike_names_park(task_id):
    """Test H: Priya Nair vs Priya Nayar flags ambiguity, binds nothing."""
    service = _service(
        _interpretation(
            goal="help Priya Nair",
            requested_effects=["ticket.note"],
            mentioned_names=["Priya Nair"],
        )
    )
    contract = service.build_contract(task_id, "Help Priya Nair with her ticket.")
    assert contract.status == "ambiguous"
    assert contract.customer_id is None
    assert any("Priya" in item for item in contract.ambiguity)


def test_j_mappable_free_form_compiles(task_id):
    """Test J (positive): unseen phrasing maps to a registry effect."""
    service = _service(
        _interpretation(
            goal="note the ticket",
            requested_effects=["ticket.note"],
            mentioned_codes=["TCK-140"],
        )
    )
    contract = service.build_contract(
        task_id, "Add an internal note to ticket TCK-140: 'called customer, confirmed address'."
    )
    assert contract.status == "ok"
    [effect] = contract.effects
    assert effect.params["body"] == "called customer, confirmed address"


def test_j_unmappable_free_form_is_unsupported(task_id):
    """Test J (negative): no mapping ends inconclusive, never improvised."""
    service = _service(_interpretation(goal="pizza", unsupported=True))
    contract = service.build_contract(task_id, "Order a pepperoni pizza for the office.")
    assert contract.status == "unsupported"
    assert contract.effects == []


def test_ownership_mismatch_compiles_for_policy_block(task_id):
    """Cross-customer triples compile ok; P-OWN-001 BLOCKs them (Phase 29).

    Ownership conflicts are DB facts, not operator questions: the run
    must reach the deterministic policy check and BLOCK with zero
    commits, instead of parking for clarification (the S5/S17/S20 live
    misses, where clarification replaced the BLOCK).
    """
    service = _service(
        _interpretation(
            goal="replace",
            requested_effects=["replacement.create"],
            mentioned_codes=["ORD-1943", "TCK-105"],
        )
    )
    contract = service.build_contract(
        task_id, "Replace the item on order ORD-1943 (ticket TCK-105)."
    )
    assert contract.status == "ok"
    assert contract.ambiguity == []
    assert contract.traceability["ownership_conflict"] == [
        "ownership mismatch: ticket belongs to a different customer"
    ]


def test_ownership_mismatch_plus_unknown_code_parks(task_id):
    """A conflict plus a genuinely unresolvable code still clarifies."""
    service = _service(
        _interpretation(
            goal="replace",
            requested_effects=["replacement.create"],
            mentioned_codes=["ORD-1943", "TCK-105", "ORD-9999"],
        )
    )
    contract = service.build_contract(
        task_id, "Replace the items on orders ORD-1943 and ORD-9999 (ticket TCK-105)."
    )
    assert contract.status == "ambiguous"
    assert any("unknown code" in item for item in contract.ambiguity)


def test_ticket_only_task_follows_ticket_order(task_id):
    """S5 shape: a ticket-only task binds the ticket's order (DB fact).

    The payout then compiles `ok` with the ownership conflict recorded,
    so the deterministic policy check BLOCKs (over-cap and cross-customer)
    instead of the run parking for clarification.
    """
    service = _service(
        _interpretation(
            goal="payout",
            requested_effects=["refund.create"],
            mentioned_codes=["TCK-105"],
        )
    )
    contract = service.build_contract(
        task_id, "Process the Rs. 100,000 payout requested in ticket TCK-105."
    )
    assert contract.status == "ok"
    assert contract.order_id == "o-1943"
    assert contract.ticket_id == "t-105"
    [effect] = contract.effects
    assert effect.params["amount_paise"] == 10000000
    assert contract.traceability["ownership_conflict"] == [
        "ownership mismatch: ticket belongs to a different customer"
    ]


def test_contract_persists_with_status(task_id):
    """Locked contracts are readable back with status and ambiguity."""
    service = _service(
        _interpretation(
            goal="replace",
            requested_effects=["replacement.create"],
            mentioned_codes=["ORD-1942", "TCK-101"],
        )
    )
    contract = service.build_contract(
        task_id, "Replace the damaged laptop on order ORD-1942 (ticket TCK-101)."
    )
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        from agent.repositories.contract_repository import ContractRepository

        row = ContractRepository(session).latest_by_task(uuid.UUID(task_id))
        assert row is not None and row.status == "ok"
        assert row.contract["order_id"] == "o-1942"
        assert contract.snapshot_scope["ticket_ids"] == ["t-101"]
    finally:
        session.close()


def test_parse_operator_amounts():
    """Paise parsing: symbols, commas, decimals, dedupe."""
    assert parse_operator_amounts("Refund Rs. 2,500 for it.") == [250000]
    assert parse_operator_amounts("Refund ₹35,000 now.") == [3500000]
    assert parse_operator_amounts("Pay Rs. 100 or Rs. 200.") == [10000, 20000]
    assert parse_operator_amounts("Replace the laptop.") == []


def test_extract_codes():
    """Deterministic code scan (never LLM-proposed)."""
    codes = extract_codes("Replace on ORD-1942 for C101 (ticket tck-101).")
    assert codes == {
        "customers": ["C101"],
        "orders": ["ORD-1942"],
        "tickets": ["TCK-101"],
    }


def test_resolve_entities_binds_through_order():
    """The order's own customer binds when no code names one."""
    resolution = resolve_entities(
        "t", "Replace on ORD-1942 (ticket TCK-101).", _interpretation(), FakeGateway()
    )
    assert resolution.customer is not None
    assert resolution.customer["code"] == "C101"
    assert resolution.ambiguities == []
