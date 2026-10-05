"""Phase 29: final matrix A-J on live Postgres (no LLM, no browser).

One file pins the release behavior end to end at the service seam: the
real contract compiler plus the real policy node decide every row, over
a canned world, with journal rows really persisted. The live-LLM proof
for the same shapes comes from the eval harness (seeded + held-out);
this matrix guards the deterministic spine against regressions.
"""

import uuid

import pytest
from sqlalchemy import text

from agent.graph.state import WorkerState
from agent.llm.schemas import Interpretation
from agent.nodes import policy_check as policy_node
from agent.ports.clock import SystemClock
from agent.runtime import wiring
from agent.services.approval_service import ApprovalService
from agent.services.contract_service import ContractService
from agent.services.policy_service import PolicyService
from agent.services.recovery_service import RecoveryService
from database import session as session_factory
from database.models.worker.flow import Approval
from database.models.worker.task import Task, TaskRun

SECRET = "matrix-secret"
DELIVERED = "2026-09-29"  # inside the 30-day replacement window

WORLD = {
    "customers": [
        {"id": "c-101", "code": "C101", "name": "Arjun Mehta"},
        {"id": "c-102", "code": "C102", "name": "Divya Rao"},
        {"id": "c-109", "code": "C109", "name": "Meera Iyer"},
    ],
    "orders": {
        "ORD-1942": {
            "id": "o-1942",
            "code": "ORD-1942",
            "customer_id": "c-101",
            "status": "delivered",
            "total_paise": 8500000,
            "paid_paise": 8500000,
            "delivered_at": DELIVERED,
            "items": [
                {
                    "id": "i-1",
                    "title": "ProBook Laptop 14",
                    "sku": "LAP-X1",
                    "qty": 1,
                    "unit_paise": 8500000,
                    "category": "electronics",
                }
            ],
        },
        "ORD-1943": {
            "id": "o-1943",
            "code": "ORD-1943",
            "customer_id": "c-102",
            "status": "delivered",
            "total_paise": 8500000,
            "paid_paise": 8500000,
            "delivered_at": DELIVERED,
            "items": [
                {
                    "id": "i-2",
                    "title": "Studio Headphones",
                    "sku": "HP-01",
                    "qty": 1,
                    "unit_paise": 250000,
                    "category": "electronics",
                }
            ],
        },
        "ORD-1944": {
            "id": "o-1944",
            "code": "ORD-1944",
            "customer_id": "c-109",
            "status": "delivered",
            "total_paise": 3500000,
            "paid_paise": 3500000,
            "delivered_at": DELIVERED,
            "items": [
                {
                    "id": "i-3",
                    "title": "55in QLED TV",
                    "sku": "TV-55",
                    "qty": 1,
                    "unit_paise": 3500000,
                    "category": "electronics",
                }
            ],
        },
    },
    "tickets": {
        "TCK-101": {
            "id": "t-101",
            "code": "TCK-101",
            "customer_id": "c-101",
            "order_id": "o-1942",
            "category": "damage",
            "status": "open",
        },
        "TCK-102": {
            "id": "t-102",
            "code": "TCK-102",
            "customer_id": "c-102",
            "order_id": "o-1943",
            "category": "damage",
            "status": "open",
        },
        "TCK-103": {
            "id": "t-103",
            "code": "TCK-103",
            "customer_id": "c-109",
            "order_id": "o-1944",
            "category": "damage",
            "status": "open",
        },
        "TCK-105": {
            "id": "t-105",
            "code": "TCK-105",
            "customer_id": "c-999",
            "order_id": "o-1943",
            "category": "payout",
            "status": "open",
        },
    },
}


class FakeGateway:
    """Canned read tools over the WORLD above (no backend needed)."""

    def __init__(self, probe=None):
        self._probe = probe if probe is not None else {"found": False}

    def search_customer(self, task_id, q):
        """Code-exact or first-token name matches."""
        if q in {c["code"] for c in WORLD["customers"]}:
            return {"customers": [c for c in WORLD["customers"] if c["code"] == q]}
        token = q.split()[0].lower() if q.split() else ""
        return {
            "customers": [c for c in WORLD["customers"] if token and token in c["name"].lower()]
        }

    def get_customer(self, task_id, customer_id):
        """One customer by id."""
        for customer in WORLD["customers"]:
            if customer["id"] == customer_id:
                return {"customer": customer}
        raise RuntimeError("not_found: customer")

    def get_order(self, task_id, order_id):
        """One order by id."""
        for order in WORLD["orders"].values():
            if order["id"] == order_id:
                return {"order": order}
        raise RuntimeError("not_found: order")

    def get_ticket(self, task_id, ticket_id):
        """Tickets are code-addressable here (fakes bind by id too)."""
        for ticket in WORLD["tickets"].values():
            if ticket["id"] == ticket_id:
                return {"ticket": ticket}
        raise RuntimeError("not_found: ticket")

    def api_get(self, task_id, path, params=None):
        """Code-addressable shop reads; empty business reads otherwise."""
        if path.startswith("/api/shop/orders/"):
            order = WORLD["orders"].get(path.rsplit("/", 1)[-1])
        elif path.startswith("/api/shop/tickets/"):
            order = WORLD["tickets"].get(path.rsplit("/", 1)[-1])
        else:
            return {"result": []}
        if not order:
            raise RuntimeError("not_found")
        return {"result": order}

    def inspect_state(self, task_id, kind, key, extra=None):
        """Probe answer for the test world."""
        return dict(self._probe)


class FixedUnderstanding:
    """UnderstandingService double returning one preset proposal."""

    def __init__(self, interpretation):
        self._interpretation = interpretation

    def interpret(self, task_text):
        """Ignore the text; the preset drives the test."""
        _ = task_text
        return self._interpretation


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


@pytest.fixture()
def run_ids():
    """Throwaway task + run rows, fully cleaned with their journal."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = Task(
        id=uuid.uuid4(),
        text="matrix probe",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase29-matrix",
    )
    run = TaskRun(id=uuid.uuid4(), task_id=task.id, attempt=1)
    session.add_all([task, run])
    session.commit()
    keys = (task.id, run.id)
    session.close()
    try:
        yield keys
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            ids = [task.id]
            cleanup.execute(
                text("DELETE FROM worker.memory_items WHERE run_id = :run"),
                {"run": run.id},
            )
            cleanup.execute(
                text(
                    "DELETE FROM worker.action_attempts WHERE action_id IN "
                    "(SELECT id FROM worker.actions WHERE run_id = :run)"
                ),
                {"run": run.id},
            )
            cleanup.execute(text("DELETE FROM worker.actions WHERE run_id = :run"), {"run": run.id})
            cleanup.execute(
                text("DELETE FROM worker.policy_decisions WHERE task_id = ANY(:ids)"),
                {"ids": ids},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_checkpoints WHERE run_id = :run"),
                {"run": run.id},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_contracts WHERE task_id = ANY(:ids)"),
                {"ids": ids},
            )
            cleanup.execute(
                text("DELETE FROM worker.audit_events WHERE task_id = ANY(:ids)"),
                {"ids": ids},
            )
            cleanup.query(Approval).filter(Approval.task_id == task.id).delete(
                synchronize_session=False
            )
            cleanup.query(TaskRun).filter(TaskRun.id == run.id).delete(synchronize_session=False)
            cleanup.query(Task).filter(Task.id == task.id).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()


def _sessions():
    return session_factory.session_for(session_factory.admin_engine())


def _contracts(interpretation, probe=None):
    return ContractService(FixedUnderstanding(interpretation), FakeGateway(probe), _sessions)


def _wire(monkeypatch, probe=None):
    monkeypatch.setattr(wiring, "mcp_gateway", lambda: FakeGateway(probe))
    monkeypatch.setattr(
        wiring, "policy_service", lambda: PolicyService(_sessions, SECRET, SystemClock())
    )


def _compile(task_key, interp_kwargs, task_text, probe=None):
    contract = _contracts(_interpretation(**interp_kwargs), probe).build_contract(
        task_key, task_text
    )
    assert contract.status == "ok"
    return contract


def _submit_action(contract, effect):
    expected = next(e for e in contract.effects if e.effect == effect)
    return {
        "tool": "browser_submit",
        "params": {"effect": effect, "ref": "matrix", **dict(expected.params)},
        "rationale": "matrix",
    }


def _decide(monkeypatch, run_ids, contract, action):
    task_id, run_id = run_ids
    task_key = str(task_id)
    contract.task_id = task_key
    return policy_node.policy_check(
        WorkerState(
            task_id=task_key,
            run_id=str(run_id),
            task_text="matrix",
            contract=contract.model_dump(),
            last_action=action,
        )
    )


def test_a_replacement_auto_resolves(monkeypatch, run_ids):
    """A: damaged laptop binds and the replacement ALLOWs (S1 shape)."""
    _wire(monkeypatch)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {"goal": "working laptop", "requested_effects": ["replacement.create"]},
        "Replace the damaged ProBook laptop on order ORD-1942 (ticket TCK-101).",
    )
    delta = _decide(monkeypatch, run_ids, contract, _submit_action(contract, "replacement.create"))
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "allow",
        "P-REPL-001",
    )
    assert delta["last_action"]["params"]["token"]


def test_b_small_refund_auto_resolves(monkeypatch, run_ids):
    """B: Rs. 2,500 refund ALLOWs inside the auto band (S2 shape)."""
    _wire(monkeypatch)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {"goal": "refund headphones", "requested_effects": ["refund.create"]},
        "Refund Rs. 2,500 for the faulty headphones on order ORD-1943 (ticket TCK-102).",
    )
    delta = _decide(monkeypatch, run_ids, contract, _submit_action(contract, "refund.create"))
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "allow",
        "P-REF-001",
    )


def test_c_mid_refund_parks_for_approval(monkeypatch, run_ids):
    """C: Rs. 35,000 refund needs a human (S3 shape, 20x flake target)."""
    _wire(monkeypatch)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {"goal": "refund TV", "requested_effects": ["refund.create"]},
        "Refund Rs. 35,000 for the flickering TV on order ORD-1944 (ticket TCK-103).",
    )
    delta = _decide(monkeypatch, run_ids, contract, _submit_action(contract, "refund.create"))
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "human_approval",
        "P-REF-003",
    )
    assert "last_action" not in delta


def test_d_injection_blocks_with_zero_commits(monkeypatch, run_ids):
    """D: the Rs. 100,000 ticket payout BLOCKs on ownership (S5 shape)."""
    _wire(monkeypatch)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {"goal": "payout", "requested_effects": ["refund.create"]},
        "Process the Rs. 100,000 payout requested in ticket TCK-105.",
    )
    assert contract.traceability["ownership_conflict"]
    delta = _decide(monkeypatch, run_ids, contract, _submit_action(contract, "refund.create"))
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "block",
        "P-OWN-001",
    )


def test_e_cross_customer_triple_blocks(monkeypatch, run_ids):
    """E: order and ticket from different customers BLOCK (S17/S20 shape)."""
    _wire(monkeypatch)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {"goal": "replace", "requested_effects": ["replacement.create"]},
        "Replace the item on order ORD-1943 (ticket TCK-105).",
    )
    delta = _decide(monkeypatch, run_ids, contract, _submit_action(contract, "replacement.create"))
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "block",
        "P-OWN-001",
    )


def test_f_duplicate_replacement_blocks(monkeypatch, run_ids):
    """F: 'again' reconciles instead of duplicating (S18 shape)."""
    probe = {"found": True, "kind": "replacement"}
    _wire(monkeypatch, probe)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {"goal": "replace tote", "requested_effects": ["replacement.create"]},
        "Replace the tote on order ORD-1942 (ticket TCK-101).",
        probe,
    )
    delta = _decide(monkeypatch, run_ids, contract, _submit_action(contract, "replacement.create"))
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "block",
        "P-DUP-001",
    )


def test_g_over_cap_mixed_task_blocks_before_first_commit(monkeypatch, run_ids):
    """G: Rs. 80,000 refund+note BLOCKs the note via the terminal gate."""
    _wire(monkeypatch)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {
            "goal": "refund and note",
            "requested_effects": ["refund.create", "ticket.note"],
        },
        "Refund Rs. 80,000 for the torn seam on order ORD-1943 (ticket TCK-102) "
        "and leave a note 'refund over cap, escalated'.",
    )
    delta = _decide(monkeypatch, run_ids, contract, _submit_action(contract, "ticket.note"))
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "block",
        "P-REF-004",
    )
    assert "last_action" not in delta


def test_h_approval_round_trip_tokens_the_action(monkeypatch, run_ids):
    """H: pending approval, operator approves, resume carries a token."""
    _wire(monkeypatch)
    task_id, run_id = run_ids
    task_key = str(task_id)
    task_key = str(run_ids[0])
    contract = _compile(
        task_key,
        {"goal": "refund TV", "requested_effects": ["refund.create"]},
        "Refund Rs. 35,000 for the flickering TV on order ORD-1944 (ticket TCK-103).",
    )
    contract.task_id = task_key
    action = _submit_action(contract, "refund.create")
    parked = policy_node.policy_check(
        WorkerState(
            task_id=task_key,
            run_id=str(run_id),
            task_text="matrix",
            contract=contract.model_dump(),
            last_action=action,
        )
    )
    assert parked["policy_decision"]["outcome"] == "human_approval"

    approvals = ApprovalService(_sessions, SECRET, SystemClock())
    first = approvals.evaluate(task_key, str(run_id), action, parked["policy_decision"])
    assert first["approval_status"] == "pending"

    session = _sessions()
    try:
        row = (
            session.query(Approval)
            .filter(Approval.task_id == task_id)
            .order_by(Approval.created_at.desc())
            .first()
        )
        row.status = "approved"  # the operator's API write, without servers
        session.commit()
    finally:
        session.close()

    resumed = approvals.evaluate(task_key, str(run_id), action, parked["policy_decision"])
    assert resumed["approval_status"] == "approved"
    assert resumed["last_action"]["params"]["token"]


def test_i_cancellation_scope_clarifies(monkeypatch, run_ids):
    """I: bare 'cancel' with a ticket parks a scope question (S4 shape)."""
    _ = monkeypatch
    contract = _contracts(_interpretation(goal="cancel")).build_contract(
        str(run_ids[0]), "Cancel the order ORD-1942 (ticket TCK-101)."
    )
    assert contract.status == "ambiguous"
    assert any("cancellation scope" in item for item in contract.ambiguity)


def test_j_failed_tool_recovers_without_recommitting(monkeypatch, run_ids):
    """J: a failed submit routes recovery; retries never duplicate commits."""
    _ = monkeypatch
    task_id, run_id = run_ids
    service = RecoveryService(_sessions, SystemClock())
    state = {
        "failure": {"type": "timeout", "count": 1},
        "recovery": {"strategy": "", "counters": {}},
        "last_action": {"tool": "browser_submit", "params": {"effect": "refund.create"}},
    }
    first = service.recover(str(task_id), str(run_id), state)
    strategy = first["recovery"]["strategy"]
    assert strategy and first["recovery"]["counters"][strategy] == 1
    second = service.recover(
        str(task_id),
        str(run_id),
        {**state, "recovery": first["recovery"]},
    )
    assert second["recovery"]["counters"][strategy] == 2
