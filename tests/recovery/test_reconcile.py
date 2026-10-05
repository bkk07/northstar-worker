"""Phase 19: probe-before-retry and reconciliation (pure + fake gateway).

Covers the plan's test list in fast form: 500-after-commit adopts with
no second submit, 500-before-commit retries once with the same key,
mismatched entities park INCONCLUSIVE, unreadable probes are bounded,
and submit counts prove no duplicate commits.
"""

from agent.contract.models import Contract
from agent.failures import reconcile as reconcile_module
from agent.failures.probe import probe_commit
from agent.runtime import mutation_keys
from agent.services.finalization_service import final_status


def _contract(**overrides):
    base = {
        "task_id": "t",
        "goal": "replace the damaged laptop",
        "effects": [
            {
                "effect": "replacement.create",
                "params": {"order_id": "o-1", "order_item_id": "i-1", "ticket_id": "t-101"},
                "capability": "replacement.create",
            }
        ],
        "capabilities": ["read", "read.fallback", "probe", "browser", "replacement.create"],
        "status": "ok",
    }
    base.update(overrides)
    return Contract(**base)


def _action(**overrides):
    base = {
        "tool": "browser_submit",
        "params": {
            "effect": "replacement.create",
            "ref": "e9",
            "order_id": "o-1",
            "order_item_id": "i-1",
            "ticket_id": "t-101",
        },
        "action_id": "00000000-0000-0000-0000-000000000001",
        "mutation_key": "key-1",
    }
    base.update(overrides)
    return base


class _FakeGateway:
    """Scripted probes + counted submits (no servers)."""

    def __init__(self, key_probe=None, identity_probe=None, submit=None):
        self.key_probe = key_probe
        self.identity_probe = identity_probe
        self.submit_result = submit
        self.submits = []
        self.probes = []

    def inspect_state(self, task_id, kind, key, extra=None):
        self.probes.append((kind, key))
        if kind == "mutation":
            if isinstance(self.key_probe, Exception):
                raise self.key_probe
            return self.key_probe or {"found": False}
        if isinstance(self.identity_probe, Exception):
            raise self.identity_probe
        return self.identity_probe or {"found": False}

    def browser_submit(self, task_id, ref, mutation_key, token, params):
        self.submits.append(mutation_key)
        return self.submit_result or {"ok": True, "status": 201}


def _service(gateway):
    from agent.services.reconciliation_service import ReconciliationService

    events = []

    class _Quiet:
        def emit(self, task_id, run_id, node, kind, **kwargs):
            events.append({"node": node, "kind": kind, **kwargs})

    service = ReconciliationService(lambda: None, gateway, None, audit=_Quiet())
    return service, events


def _state(action, **overrides):
    base = {
        "task_id": "t",
        "run_id": "r",
        "contract": _contract().model_dump(),
        "failure": {"type": "unknown_outcome", "count": 1},
        "last_action": action,
    }
    base.update(overrides)
    return base


def test_keys_stable_across_retries():
    """Same binding, fresh ref/token → same key (idempotent retries)."""
    first = {
        "effect": "replacement.create",
        "ref": "e5",
        "token": "a",
        "order_id": "o-1",
        "ticket_id": "t-101",
    }
    retry = {
        "effect": "replacement.create",
        "ref": "e9",
        "token": "b",
        "order_id": "o-1",
        "ticket_id": "t-101",
    }
    assert mutation_keys.key_for("t", "browser_submit", first) == (
        mutation_keys.key_for("t", "browser_submit", retry)
    )


def test_keys_differ_per_binding():
    """Different effects/params never share a key (no cross-talk)."""
    one = mutation_keys.key_for("t", "browser_submit", {"effect": "a", "order_id": "o-1"})
    other = mutation_keys.key_for("t", "browser_submit", {"effect": "a", "order_id": "o-2"})
    assert one != other and len(one) == 32


def test_500_after_commit_adopts_without_resubmit():
    """S6 shape: probe finds the row → reconciled, zero submits."""
    gateway = _FakeGateway(key_probe={"found": True, "kind": "replacement", "entity_id": "r-1"})
    service, events = _service(gateway)
    delta = service.probe_and_decide("t", "r", _state(_action()))
    assert delta["probe_status"] == "exists"
    assert delta["observation_status"] == "success"
    assert delta["reconciled_entity"]["entity_id"] == "r-1"
    assert gateway.submits == [], "adopted rows are never resubmitted"
    assert events and events[0]["kind"] == "recovery.probe"


def test_identity_probe_catches_keyless_commit():
    """Key never reached the server, but the row exists → still adopt."""
    gateway = _FakeGateway(
        identity_probe={"found": True, "kind": "replacement", "entity_id": "r-2"}
    )
    service, _ = _service(gateway)
    delta = service.probe_and_decide("t", "r", _state(_action()))
    assert delta["probe_status"] == "exists"
    assert delta["reconciled_entity"]["via"] == "business_identity"
    assert gateway.submits == []


def test_500_before_commit_retries_once_same_key():
    """Probe finds nothing → one retry reusing the failed key."""
    gateway = _FakeGateway()
    service, _ = _service(gateway)
    delta = service.probe_and_decide("t", "r", _state(_action()))
    assert delta["probe_status"] == "absent"
    assert delta["last_action"]["reuse_key"] == "key-1"


def test_mismatched_entity_parks_inconclusive():
    """A foreign row is a human's call, never an adoption."""
    gateway = _FakeGateway(key_probe={"found": True, "kind": "refund", "entity_id": "x-9"})
    service, _ = _service(gateway)
    delta = service.probe_and_decide("t", "r", _state(_action()))
    assert delta["probe_status"] == "mismatch"
    assert final_status({"probe_status": "mismatch"}) == "inconclusive"


def test_unreadable_probes_bounded_then_parked():
    """Dead probes retry the submit while budget lasts, then park."""
    gateway = _FakeGateway(key_probe=RuntimeError("down"), identity_probe=RuntimeError("down"))
    service, _ = _service(gateway)
    first = service.probe_and_decide("t", "r", _state(_action()))
    assert first["probe_status"] == "absent", "key protects the blind retry"
    third = service.probe_and_decide("t", "r", _state(_action(), probe_attempts=2))
    assert third["probe_status"] == "mismatch"
    assert final_status(third) == "inconclusive"


def test_search_before_create_skips_submit():
    """The entity already exists → adopted pre-submit, one probe, no commit."""
    from agent.services.execution_service import ExecutionService

    gateway = _FakeGateway(
        identity_probe={"found": True, "kind": "replacement", "entity_id": "r-3"},
        submit={"ok": True, "status": 201},
    )
    service = ExecutionService.__new__(ExecutionService)
    service._gateway = gateway
    calls = {"started": [], "finished": False}

    class _Journal:
        def start_action(self, *args, **kwargs):
            from uuid import UUID

            from agent.runtime.journal import StartedAction

            row = StartedAction(
                action_id=UUID("00000000-0000-0000-0000-000000000001"),
                seq=0,
                mutation_key="k",
            )
            calls["started"].append(row)
            return row

        def begin_attempt(self, *args):
            raise AssertionError("no attempt should open for an adoption")

        def finish_action(self, *args):
            calls["finished"] = True

    service._journal = _Journal()
    action = _action()
    del action["action_id"]
    result = service.execute("t", "r", action)
    assert result.ok and result.mutated is False
    assert result.payload["reconciled"] is True
    assert gateway.submits == [], "search-before-create commits nothing"
    assert gateway.probes, "the identity probe ran first"


def test_reconcile_rejects_out_of_scope_effect():
    """Probe hits outside the contract never adopt (fail closed)."""
    hit = type("H", (), {"kind": "refund", "entity_id": "x", "via": "mutation_key"})()
    verdict, _ = reconcile_module.reconcile_hit(
        hit, _contract(), {"params": {"effect": "refund.create", "order_id": "o-9"}}
    )
    assert verdict == reconcile_module.MISMATCH


def test_probe_never_raises_on_shapes():
    """Malformed payloads degrade to not-found (probe is best-effort)."""
    gateway = _FakeGateway(key_probe={"weird": 1}, identity_probe="nope")
    outcome = probe_commit(gateway, "t", "k", {})
    assert outcome.key_hit.found is False
    assert outcome.identity_hit is None or outcome.identity_hit.found is False
