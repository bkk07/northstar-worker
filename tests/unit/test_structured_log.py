"""Structured log fields: every line carries the run context (Phase 24)."""

import json

from agent.runtime.log import log_event


def test_log_line_has_structured_fields(capsys):
    """Operators grep one field; prose never replaces the record."""
    log_event("runner", "run.end", task_id="t1", run_id="r1", status="succeeded", steps=9)
    line = capsys.readouterr().out.strip()
    record = json.loads(line)
    assert record["component"] == "runner"
    assert record["event"] == "run.end"
    assert record["task_id"] == "t1"
    assert record["run_id"] == "r1"
    assert record["status"] == "succeeded"
    assert record["steps"] == 9
    assert "ts" in record


def test_none_fields_dropped(capsys):
    """Absent context stays absent (no null noise)."""
    log_event("runner", "run.start", task_id="t1", run_id=None)
    record = json.loads(capsys.readouterr().out.strip())
    assert "run_id" not in record
    assert record["task_id"] == "t1"
