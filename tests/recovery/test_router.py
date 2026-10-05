"""Phase 18: router coverage, bounds, fallbacks, and the recover node."""

from agent.contract.models import Contract
from agent.failures import router, taxonomy
from agent.failures.strategies import SEARCH_FALLBACKS, apply_strategy


def _contract(**overrides):
    base = {
        "task_id": "t",
        "goal": "replace the damaged laptop",
        "effects": [],
        "capabilities": ["read", "read.fallback", "probe", "browser"],
        "status": "ok",
    }
    base.update(overrides)
    return Contract(**base)


def _state(**overrides):
    base = {
        "task_id": "t",
        "run_id": "r",
        "contract": _contract().model_dump(),
        "failure": {"type": "network_error", "count": 1},
        "last_action": {"tool": "get_order", "params": {}},
    }
    base.update(overrides)
    return base


def test_router_covers_all_fourteen():
    """Every taxonomy type routes somewhere (never an unhandled failure)."""
    assert set(router.ROUTES) == taxonomy.ALL_TYPES
    for failure_type in taxonomy.ALL_TYPES:
        strategy, _ = router.route(failure_type, {})
        assert strategy in (
            "re_observe",
            "re_discover",
            "re_plan",
            "retry",
            "fallback_tool",
            "terminate_safely",
        )


def test_retry_bounds_terminate():
    """Exhausted retries end the run (recovery never loops forever)."""
    strategy, _ = router.route("network_error", {})
    assert strategy == "retry"
    strategy, _ = router.route("network_error", {"retry": 3})
    assert strategy == "terminate_safely"


def test_backoff_grows_exponentially():
    """Bounded retries wait longer each round (thundering herds lose)."""
    assert router.backoff_ms(0) == 500
    assert router.backoff_ms(1) == 1000
    assert router.backoff_ms(2) == 2000
    assert router.backoff_ms(99) == 5000


def test_s7_search_falls_back_to_api():
    """S7 shape: dead UI search rewrites to api_get inside scope."""
    state = _state(
        failure={"type": "element_not_found", "count": 1},
        last_action={"tool": "search_customer", "params": {"q": "ada"}},
    )
    delta = apply_strategy("fallback_tool", state, _contract(), "element_not_found")
    action = delta["last_action"]
    assert action["tool"] == "api_get"
    assert action["params"]["path"] == "/api/read/customers"
    assert action["params"]["params"] == {"q": "ada"}


def test_fallback_outside_scope_terminates():
    """Fallbacks stay in capability scope (never an unscoped tool call)."""
    narrow = _contract(capabilities=["read", "probe", "browser"])
    delta = apply_strategy(
        "fallback_tool",
        _state(last_action={"tool": "search_customer", "params": {"q": "x"}}),
        narrow,
        "element_not_found",
    )
    assert delta == {"recovery_override": "terminate_safely"}


def test_fallback_covers_every_search_tool():
    """Each fallback-tagged tool has a search mapping (no dead routes)."""
    from agent.contract.action_validator import TOOL_META

    tagged = {name for name, meta in TOOL_META.items() if meta.fallback_for == "api_get"}
    assert tagged == set(SEARCH_FALLBACKS)


def test_s9_session_expiry_marks_relogin():
    """S9 shape: expiry re-observes with a re-login marker."""
    delta = apply_strategy("re_observe", _state(), _contract(), "session_expired")
    assert delta == {"relogin": True}


def test_s10_validation_keeps_correction_context():
    """S10 shape: the 422 correction loop keeps its error and count."""
    state = _state(validation_error="binding: amount mismatch", validation_failures=1)
    delta = apply_strategy("re_observe", state, _contract(), "validation_error")
    assert delta == {"validation_failures": 2}


def test_stale_ref_reobserves_without_reset():
    """Stale refs rebind on the next observe (plan and cursor survive)."""
    delta = apply_strategy("re_observe", _state(), _contract(), "stale_reference")
    assert delta == {}


def test_no_strategy_retries_a_submit():
    """No recovery path duplicates a side effect (submits never retry)."""
    for failure_type in ("unknown_outcome", "conflict_duplicate"):
        strategy, _ = router.route(failure_type, {})
        assert strategy == "terminate_safely"


def test_recover_node_routes_counts_and_audits(monkeypatch):
    """The node wires router + counters + recovery.* audit together."""
    from agent.nodes import recover as recover_node
    from agent.runtime import wiring

    events = []

    class _FakeAudit:
        def emit(self, task_id, run_id, node, kind, **kwargs):
            events.append({"node": node, "kind": kind, **kwargs})

    class _FakeService:
        def recover(self, task_id, run_id, state):
            assert (task_id, run_id) == ("t", "r")
            service = _real_service()
            return service.recover(task_id, run_id, state)

    def _real_service():
        from agent.services.recovery_service import RecoveryService

        return RecoveryService(lambda: None, None, audit=_FakeAudit())

    monkeypatch.setattr(wiring, "recovery_service", lambda: _FakeService())
    delta = recover_node.recover(_state())
    assert delta["recovery"] == {"strategy": "retry", "counters": {"retry": 1}}
    assert delta["backoff_ms"] == 500
    assert events and events[0]["kind"] == "recovery.decided"
    assert events[0]["error_type"] == "network_error"


def test_second_round_bumps_counters(monkeypatch):
    """Counters accumulate across rounds (the bound is reachable)."""
    from agent.nodes import recover as recover_node
    from agent.runtime import wiring

    class _Quiet:
        def emit(self, *args, **kwargs):
            pass

    def _service():
        from agent.services.recovery_service import RecoveryService

        return RecoveryService(lambda: None, None, audit=_Quiet())

    monkeypatch.setattr(wiring, "recovery_service", _service)
    first = recover_node.recover(_state())
    second = recover_node.recover(_state(recovery=first["recovery"]))
    assert second["recovery"]["counters"] == {"retry": 2}
    assert second["backoff_ms"] == 1000


def test_unknown_type_terminates(monkeypatch):
    """Unrecognized failure types fail closed (never improvise)."""
    from agent.nodes import recover as recover_node
    from agent.runtime import wiring

    class _Quiet:
        def emit(self, *args, **kwargs):
            pass

    def _service():
        from agent.services.recovery_service import RecoveryService

        return RecoveryService(lambda: None, None, audit=_Quiet())

    monkeypatch.setattr(wiring, "recovery_service", _service)
    delta = recover_node.recover(_state(failure={"type": "nope", "count": 1}))
    assert delta["recovery"]["strategy"] == "terminate_safely"
