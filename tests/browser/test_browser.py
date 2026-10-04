"""Phase 10: Playwright layer against the real `/ops` console."""

import pytest

from browser.errors import ElementNotFound, GuardViolation, StaleReference
from browser.manager import SessionManager
from browser.observer import dump_text


def _login(session, agent_name="browser-probe"):
    """Drive the ops login form purely by refs; return the queue observation."""
    session.navigate("/ops/login")
    observation = session.observe()
    name_ref = next(r.ref for r in observation.find(role="textbox") if "agent" in r.name.lower())
    login_ref = next(r.ref for r in observation.find(role="button", name="log in"))
    session.fill(name_ref, agent_name)
    session.click(login_ref)
    return session.observe()


def test_observe_ops_login(session):
    """Observation finds named refs for every login control."""
    observation = session.navigate("/ops/login")
    assert "/ops/login" in observation.url
    assert observation.find(role="textbox")
    assert observation.find(role="button", name="log in")
    shot = session.screenshot("login-page")
    assert shot.endswith("login-page.png")
    assert observation.page_version


def test_fill_and_click_by_ref_login(session):
    """Fill + click by ref lands on the ticket queue (no selectors)."""
    queue = _login(session)
    assert "/ops/tickets" in queue.url
    assert any("TCK-" in (target.name or "") for target in queue.find())


def test_stale_ref_after_rerender(session):
    """Old version + unknown ref fail fast with the right errors."""
    before = session.navigate("/ops/login")
    _login(session)
    after = session.observe()
    assert after.page_version != before.page_version
    stale_ref = next(iter(before.refs))
    with pytest.raises(StaleReference):
        session.click(stale_ref, expected_version=before.page_version)
    with pytest.raises(ElementNotFound):
        session.click("e9999")


def test_guard_blocks_worker_and_control(session):
    """`/worker` and `/api/control` are unreachable; `/ops` works."""
    with pytest.raises(GuardViolation):
        session.navigate("/worker")
    with pytest.raises(GuardViolation):
        session.navigate("/api/control/seed")
    with pytest.raises(GuardViolation):
        session.navigate("http://example.com/ops")
    observation = session.navigate("/ops/login")
    assert "/ops/login" in observation.url


def test_mutation_status_captured(session):
    """A UI note commit surfaces its HTTP status in network capture."""
    _login(session)
    session.navigate("/ops/tickets/TCK-140")
    observation = session.observe()
    body_ref = next(r.ref for r in observation.find(role="textbox") if r.name == "Note text")
    add_ref = next(r.ref for r in observation.find(role="button") if r.name.lower() == "add note")
    session.network.clear()
    session.fill(body_ref, "Browser-layer probe note.")
    session.click(add_ref)
    session.observe()
    assert session.network.last_status("/api/ops/tickets/") == 201


def test_session_survives_context_restart(servers, run_dirs):
    """Storage state restores the login across a full context restart."""
    from browser.session import BrowserSession

    storage, shots = run_dirs
    first = BrowserSession(
        "restart-probe", frontend_origin=servers["frontend"], storage_dir=storage
    ).start()
    try:
        _login(first, agent_name="restart-probe")
        first.save_storage_state()
    finally:
        first.stop()

    second = BrowserSession(
        "restart-probe", frontend_origin=servers["frontend"], storage_dir=storage
    ).start()
    try:
        queue = second.navigate("/ops/tickets")
        assert "/ops/tickets" in queue.url
        assert any("TCK-" in (target.name or "") for target in queue.find())
    finally:
        second.stop()


def test_manager_lifecycle(servers, run_dirs):
    """Manager opens, gets, and closes sessions by run id."""
    storage, shots = run_dirs
    manager = SessionManager(
        frontend_origin=servers["frontend"], storage_dir=storage, screenshot_dir=shots
    )
    try:
        session = manager.open("managed-run")
        assert session.started
        assert manager.get("managed-run") is session
        observation = session.navigate("/ops/login")
        assert "/ops/login" in observation.url
    finally:
        manager.close("managed-run")
        manager.close_all()
    assert dump_text.__name__ == "dump_text"
