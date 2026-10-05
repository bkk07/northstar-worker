"""Observation normalization: every outcome lands in one bucket."""

from agent.services.observation_service import ObservationService


class _FakeSession:
    """Capture memory rows without a database."""

    def __init__(self):
        self.rows = []

    def add(self, row):
        self.rows.append(row)

    def flush(self):
        pass

    def refresh(self, row):
        return row

    def commit(self):
        pass

    def close(self):
        pass


def _service():
    sessions = []

    def factory():
        session = _FakeSession()
        sessions.append(session)
        return session

    return ObservationService(factory), sessions


def _action(tool="browser_observe"):
    return {"tool": tool, "params": {}, "seq": 0}


def test_submit_ok_is_effects_done():
    """A landed commit verifies next (hero-path routing)."""
    service, _ = _service()
    verdict = service.observe(
        "t",
        "00000000-0000-0000-0000-000000000000",
        _action("browser_submit"),
        {
            "ok": True,
            "payload": {"ok": True, "status": 201, "effect": "replacement.create"},
            "mutated": True,
            "mutation_key": "k",
        },
    )
    assert verdict.status == "effects_done"
    assert verdict.observation["mutated"] is True
    assert verdict.observation["status"] == 201


def test_read_ok_is_success():
    """Reads keep the loop acting (decide proposes next)."""
    service, _ = _service()
    verdict = service.observe(
        "t",
        "00000000-0000-0000-0000-000000000000",
        _action("browser_observe"),
        {"ok": True, "payload": {"url": "http://x/", "refs": {}}, "mutation_key": "k"},
    )
    assert verdict.status == "success"
    assert verdict.observation["payload"]["url"] == "http://x/"


def test_tool_error_is_failure():
    """Exceptions route to classify (Phase 17 fills the taxonomy)."""
    service, _ = _service()
    verdict = service.observe(
        "t",
        "00000000-0000-0000-0000-000000000000",
        _action("browser_click"),
        {"ok": False, "error": "boom", "error_type": "RuntimeError", "mutation_key": "k"},
    )
    assert verdict.status == "failure"
    assert verdict.observation["error"] == "boom"
    assert verdict.observation["mutated"] is False


def test_memory_rows_carry_provenance():
    """Page data is untrusted; DB reads are trusted."""
    service, sessions = _service()
    run = "00000000-0000-0000-0000-000000000000"
    service.observe(
        "t", run, _action("browser_observe"), {"ok": True, "payload": {}, "mutation_key": "k"}
    )
    service.observe(
        "t", run, _action("get_ticket"), {"ok": True, "payload": {"id": "x"}, "mutation_key": "k"}
    )
    rows = sessions[0].rows + sessions[1].rows
    by_source = {row.source_type: row.trust for row in rows}
    assert by_source == {"browser": "untrusted", "database": "trusted"}
    assert all(str(row.run_id) == run for row in rows)
