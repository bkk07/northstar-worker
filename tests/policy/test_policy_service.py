"""Policy service + node: persistence, tokens, and state deltas (Phase 15).

Real `ns_runner` writes on live Postgres with hand-built facts; the
gateway is faked because fact-gathering shape is covered by unit tests
and live runs in the manual check.
"""

import uuid
from datetime import UTC, datetime

import pytest

from agent.contract.models import Contract, ExpectedEffect
from agent.graph.state import WorkerState
from agent.nodes import policy_check as policy_node
from agent.policy.facts import Facts
from agent.ports.clock import ClockPort
from agent.repositories.action_repository import ActionRepository
from agent.repositories.policy_decision_repository import PolicyDecisionRepository
from agent.runtime import wiring
from agent.services.policy_service import PolicyService
from database import session as session_factory
from database.models.worker.action import Action
from database.models.worker.audit import AuditEvent
from database.models.worker.flow import PolicyDecision
from database.models.worker.task import Task, TaskRun
from mcp_server.token_guard import verify_submit_token
from northstar_common.tokens import canonical_params_hash
from tests.policy.conftest import TODAY, order, ticket


class _FixedClock:
    """Pinned date for deterministic windows."""

    def now(self):
        """Midnight UTC on the pinned test date."""
        return datetime(TODAY.year, TODAY.month, TODAY.day, tzinfo=UTC)


def _contract(amount=250000, task_id="t1"):
    return Contract(
        task_id=task_id,
        goal="refund",
        customer_id="c-101",
        order_id="o-1942",
        ticket_id="t-101",
        effects=[
            ExpectedEffect(
                effect="refund.create",
                params={"order_id": "o-1942", "ticket_id": "t-101", "amount_paise": amount},
                capability="refund.create",
            )
        ],
        capabilities=["read", "read.fallback", "probe", "browser", "refund.create"],
        status="ok",
    )


def _facts(**overrides):
    base = {
        "customer_id": "c-101",
        "order": order(
            paid=250000,
            items=[
                {
                    "id": "i-1",
                    "title": "H",
                    "sku": "H",
                    "qty": 1,
                    "unit_paise": 250000,
                    "category": "electronics",
                }
            ],
        ),
        "ticket": ticket(category="refund"),
        "customer": {"id": "c-101"},
    }
    base.update(overrides)
    return Facts(**base)


def _submit(amount=250000):
    return {
        "tool": "browser_submit",
        "params": {
            "effect": "refund.create",
            "ref": "e5",
            "order_id": "o-1942",
            "ticket_id": "t-101",
            "amount_paise": amount,
        },
        "rationale": "test",
    }


@pytest.fixture()
def run_ids():
    """Throwaway task + run rows, cleaned up with their journal."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = Task(
        id=uuid.uuid4(),
        text="policy probe",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase15-test",
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
            for model, column in (
                (PolicyDecision, PolicyDecision.run_id),
                (Action, Action.run_id),
                (AuditEvent, AuditEvent.run_id),
            ):
                cleanup.query(model).filter(column == run.id).delete(synchronize_session=False)
            cleanup.query(TaskRun).filter(TaskRun.id == run.id).delete(synchronize_session=False)
            cleanup.query(Task).filter(Task.id == task.id).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()


def _service():
    sessions = lambda: session_factory.session_for(session_factory.admin_engine())  # noqa: E731
    return PolicyService(sessions, "test-secret", _FixedClock())


def test_allow_submit_persists_and_issues_token(run_ids):
    """ALLOW writes the audit row, links the action, and owes a token."""
    task_id, run_id = run_ids
    task_key = str(task_id)
    engine = session_factory.admin_engine()
    setup = session_factory.session_for(engine)
    action = _submit()
    ActionRepository(setup).reserve(
        run_id,
        "write",
        action["tool"],
        action["params"],
        canonical_params_hash(action["params"]),
        "write",
    )
    setup.commit()
    setup.close()

    result = _service().check_and_persist(
        task_key, str(run_id), action, _contract(task_id=task_key), _facts()
    )
    assert result.outcome == "allow" and result.rule_id == "P-REF-001"
    assert result.token
    verify_submit_token(result.token, "test-secret", task_key, dict(action["params"]))

    check = session_factory.session_for(engine)
    try:
        rows = PolicyDecisionRepository(check).list_by_run(run_id)
        assert len(rows) == 1
        assert rows[0].rule_id == "P-REF-001" and rows[0].outcome == "allow"
        assert rows[0].action_id is not None
    finally:
        check.close()


def test_approval_and_block_owe_no_token(run_ids):
    """Only ALLOW commits carry tokens; pauses and blocks carry reasons."""
    task_id, run_id = run_ids
    task_key = str(task_id)
    service = _service()
    approval = service.check_and_persist(
        task_key,
        str(run_id),
        _submit(3500000),
        _contract(3500000, task_key),
        _facts(order=order(paid=9000000)),
    )
    assert approval.outcome == "human_approval" and approval.token == ""
    blocked = service.check_and_persist(
        task_key,
        str(run_id),
        _submit(9000001),
        _contract(9000001, task_key),
        _facts(order=order(paid=9000000)),
    )
    assert blocked.outcome == "block" and blocked.token == ""


def test_policy_node_attaches_token(monkeypatch, run_ids):
    """The node delta carries the decision and the tokened action."""
    task_id, run_id = run_ids

    class _Gateway:
        def get_customer(self, task_id, customer_id):
            """Canned customer read."""
            return {"customer": {"id": "c-101"}}

        def get_order(self, task_id, order_id):
            """Canned order read."""
            return {"order": _facts().order}

        def get_ticket(self, task_id, ticket_id):
            """Canned ticket read."""
            return {"ticket": _facts().ticket}

        def inspect_state(self, task_id, kind, key, extra=None):
            """No existing mutations in this world."""
            return {"found": False}

        def api_get(self, task_id, path, params=None):
            """Empty policies and history (code defaults apply)."""
            return {"result": []}

    monkeypatch.setattr(wiring, "mcp_gateway", lambda: _Gateway())
    real_service = _service()
    monkeypatch.setattr(wiring, "policy_service", lambda: real_service)

    action = _submit()
    task_key = str(task_id)
    contract = _contract(task_id=task_key)
    delta = policy_node.policy_check(
        WorkerState(
            task_id=task_key,
            run_id=str(run_id),
            task_text="x",
            contract=contract.model_dump(),
            last_action=action,
        )
    )
    assert delta["policy_decision"]["outcome"] == "allow"
    assert delta["policy_decision"]["rule_id"] == "P-REF-001"
    assert delta["last_action"]["params"]["token"]
    verify_submit_token(
        delta["last_action"]["params"]["token"],
        "test-secret",
        task_key,
        dict(action["params"]),
    )


def test_clock_port_contract():
    """SystemClock satisfies the protocol the service depends on."""
    assert isinstance(wiring.system_clock(), ClockPort)


def _note_action():
    return {
        "tool": "browser_submit",
        "params": {
            "effect": "ticket.note",
            "ref": "e9",
            "ticket_id": "t-101",
            "kind": "internal",
            "body": "status update",
        },
        "rationale": "test",
    }


def _mixed_contract(amount, task_key, major="refund.create"):
    if major == "refund.create":
        major_effect = ExpectedEffect(
            effect="refund.create",
            params={"order_id": "o-1942", "ticket_id": "t-101", "amount_paise": amount},
            capability="refund.create",
        )
    else:
        major_effect = ExpectedEffect(
            effect="replacement.create",
            params={"order_id": "o-1942", "order_item_id": "i-1", "ticket_id": "t-101"},
            capability="replacement.create",
        )
    effects = [
        major_effect,
        ExpectedEffect(
            effect="ticket.note",
            params={"ticket_id": "t-101", "kind": "internal", "body": "status update"},
            capability="ticket.note",
        ),
    ]
    return Contract(
        task_id=task_key,
        goal="major and note",
        customer_id="c-101",
        order_id="o-1942",
        ticket_id="t-101",
        effects=effects,
        capabilities=["read", "read.fallback", "probe", "browser", major, "ticket.note"],
        status="ok",
    )


class _GateGateway:
    """Canned reads; probes configurable per test (dup worlds included)."""

    def __init__(self, order=None, ticket=None, probe=None):
        self._order = order
        self._ticket = ticket
        self._probe = probe if probe is not None else {"found": False}

    def get_customer(self, task_id, customer_id):
        """Canned customer read."""
        return {"customer": {"id": "c-101"}}

    def get_order(self, task_id, order_id):
        """Canned order read."""
        return {"order": self._order or _facts().order}

    def get_ticket(self, task_id, ticket_id):
        """Canned ticket read."""
        return {"ticket": self._ticket or _facts().ticket}

    def inspect_state(self, task_id, kind, key, extra=None):
        """Probe answer for the test world."""
        return dict(self._probe)

    def api_get(self, task_id, path, params=None):
        """Empty policies and history (code defaults apply)."""
        return {"result": []}


def _wire(monkeypatch, gateway=None):
    monkeypatch.setattr(wiring, "mcp_gateway", lambda: gateway or _GateGateway())
    monkeypatch.setattr(wiring, "policy_service", lambda: _service())


def _check(monkeypatch, run_ids, contract, action):
    task_id, run_id = run_ids
    task_key = str(task_id)
    contract.task_id = task_key
    return (
        policy_node.policy_check(
            WorkerState(
                task_id=task_key,
                run_id=str(run_id),
                task_text="x",
                contract=contract.model_dump(),
                last_action=action,
            )
        ),
        task_key,
        run_id,
    )


def test_terminal_gate_blocks_note_ahead_of_over_cap_refund(monkeypatch, run_ids):
    """S914 shape: the note dies with the doomed refund (zero commits)."""
    _wire(monkeypatch, _GateGateway(order=order(paid=9000000)))
    task_key = str(run_ids[0])
    delta, _, run_id = _check(
        monkeypatch, run_ids, _mixed_contract(8000000, task_key), _note_action()
    )
    decision = delta["policy_decision"]
    assert (decision["outcome"], decision["rule_id"]) == ("block", "P-REF-004")
    assert "terminal refund.create would block" in decision["reason"]
    assert "last_action" not in delta  # no token for a held note
    check = session_factory.session_for(session_factory.admin_engine())
    try:
        rows = PolicyDecisionRepository(check).list_by_run(run_id)
        assert len(rows) == 1 and rows[0].rule_id == "P-REF-004"
        assert rows[0].params["effect"] == "refund.create"
    finally:
        check.close()


def test_terminal_gate_blocks_note_on_ownership_mismatch(monkeypatch, run_ids):
    """Ownership-doomed tasks post nothing before the BLOCK."""
    _wire(monkeypatch, _GateGateway(ticket=ticket(customer="c-102")))
    task_key = str(run_ids[0])
    contract = _mixed_contract(0, task_key, major="replacement.create")
    delta, _, _ = _check(monkeypatch, run_ids, contract, _note_action())
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "block",
        "P-OWN-001",
    )


def test_terminal_gate_blocks_note_ahead_of_duplicate(monkeypatch, run_ids):
    """Duplicate-doomed tasks end before the first commit (probes loaded)."""
    _wire(monkeypatch, _GateGateway(probe={"found": True, "kind": "refund"}))
    task_key = str(run_ids[0])
    delta, _, _ = _check(monkeypatch, run_ids, _mixed_contract(250000, task_key), _note_action())
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "block",
        "P-DUP-001",
    )


def test_terminal_gate_passes_healthy_note(monkeypatch, run_ids):
    """Healthy mixed tasks keep their notes (gate is BLOCK-only)."""
    _wire(monkeypatch)
    task_key = str(run_ids[0])
    delta, _, _ = _check(monkeypatch, run_ids, _mixed_contract(250000, task_key), _note_action())
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "allow",
        "P-NOTE-001",
    )
    assert delta["last_action"]["params"]["token"]


def test_terminal_gate_passes_note_when_refund_needs_approval(monkeypatch, run_ids):
    """Approval flows keep their notes; the refund still parks for HITL."""
    _wire(monkeypatch, _GateGateway(order=order(paid=9000000)))
    task_key = str(run_ids[0])
    delta, _, _ = _check(monkeypatch, run_ids, _mixed_contract(3500000, task_key), _note_action())
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "allow",
        "P-NOTE-001",
    )


def test_terminal_gate_skips_committed_major(monkeypatch, run_ids):
    """Post-commit notes still flow after the refund executed."""
    _wire(monkeypatch)
    task_id, run_id = run_ids
    task_key = str(task_id)
    engine = session_factory.admin_engine()
    setup = session_factory.session_for(engine)
    try:
        setup.add(
            Action(
                run_id=run_id,
                seq=0,
                kind="write",
                tool="browser_submit",
                params={"effect": "refund.create", "order_id": "o-1942", "ticket_id": "t-101"},
                params_hash="committed-major",
                side_effect="write",
                status="done",
            )
        )
        setup.commit()
    finally:
        setup.close()
    delta, _, _ = _check(monkeypatch, run_ids, _mixed_contract(250000, task_key), _note_action())
    assert (delta["policy_decision"]["outcome"], delta["policy_decision"]["rule_id"]) == (
        "allow",
        "P-NOTE-001",
    )
