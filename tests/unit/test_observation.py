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


def test_screenshot_paths_indexed_as_evidence():
    """Screenshot results land in the evidence trail, not just memory."""
    from database.models.worker.evidence import Evidence

    service, sessions = _service()
    task = "11111111-1111-1111-1111-111111111111"
    run = "00000000-0000-0000-0000-000000000000"
    verdict = service.observe(
        task,
        run,
        {"tool": "browser_screenshot", "params": {"label": "queue"}, "seq": 0},
        {"ok": True, "payload": {"path": "shots/queue.png"}, "mutation_key": "k"},
    )
    assert verdict.status == "success"
    shots = [row for session in sessions for row in session.rows if isinstance(row, Evidence)]
    assert len(shots) == 1
    assert shots[0].packet["type"] == "screenshot/v1"
    assert shots[0].packet["label"] == "queue"
    assert shots[0].packet["path"] == "shots/queue.png"
    assert str(shots[0].task_id) == task


def test_submit_screenshots_indexed_before_and_after():
    """Submits index their before/after screenshots for the packet."""
    from database.models.worker.evidence import Evidence

    service, sessions = _service()
    task = "11111111-1111-1111-1111-111111111111"
    run = "00000000-0000-0000-0000-000000000000"
    service.observe(
        task,
        run,
        _action("browser_submit"),
        {
            "ok": True,
            "payload": {
                "ok": True,
                "status": 201,
                "effect": "replacement.create",
                "before_screenshot": "shots/before.png",
                "after_screenshot": "shots/after.png",
            },
            "mutated": True,
            "mutation_key": "k",
        },
    )
    shots = [row for session in sessions for row in session.rows if isinstance(row, Evidence)]
    assert [(shot.packet["label"], shot.packet["path"]) for shot in shots] == [
        ("before-submit", "shots/before.png"),
        ("after-submit", "shots/after.png"),
    ]
