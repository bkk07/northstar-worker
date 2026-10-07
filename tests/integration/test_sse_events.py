"""Live task events over SSE: order, resume, live arrival (Phase 25).

The app serves the stream from a uvicorn subprocess (this starlette
TestClient buffers full responses, so real HTTP carries the stream).
Generator mechanics — resume filtering, disconnect cleanup, heartbeat —
are pinned directly against `task_event_stream` in-process.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.schemas.worker.events import AuditEventRead
from app.sse.listener import subscriber_count
from app.sse.stream import format_event, task_event_stream
from database import session as session_factory
from tests.integration.conftest import staff_headers

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _free_port() -> int:
    """An ephemeral port (closed at once; the server binds it next)."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(scope="module")
def server_url():
    """Uvicorn with the real app (terminated after the module)."""
    port = _free_port()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        (ROOT, os.path.join(ROOT, "backend"), os.path.join(ROOT, "common"))
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            os.path.join(ROOT, "backend"),
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{url}/api/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            raise RuntimeError("test server never became ready")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=15)


@pytest.fixture()
def task_rows():
    """Throwaway task with three ordered audit rows."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task_id = uuid.uuid4()
    session.execute(
        text(
            "INSERT INTO worker.tasks (id, text, mode, status, current_state, created_by) "
            "VALUES (:id, 'sse probe', 'explicit', 'running', 'running', 'phase25-test')"
        ),
        {"id": str(task_id)},
    )
    seqs = []
    for kind in ("run.start", "policy.decision", "run.end"):
        row = session.execute(
            text(
                "INSERT INTO worker.audit_events "
                "(id, task_id, ts, kind, retry_count, payload) "
                "VALUES (:id, :task, now(), :kind, 0, '{}') RETURNING seq"
            ),
            {"id": str(uuid.uuid4()), "task": str(task_id), "kind": kind},
        ).scalar()
        seqs.append(row)
    session.commit()
    session.close()
    try:
        yield task_id, seqs
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text("DELETE FROM worker.audit_events WHERE task_id = :id"),
                {"id": str(task_id)},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_runs WHERE task_id = :id"),
                {"id": str(task_id)},
            )
            cleanup.execute(text("DELETE FROM worker.tasks WHERE id = :id"), {"id": str(task_id)})
            cleanup.commit()
        finally:
            cleanup.close()


def _insert_event(task_id, kind="tool.call"):
    """One live audit row (fires the NOTIFY trigger on commit)."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    try:
        session.execute(
            text(
                "INSERT INTO worker.audit_events "
                "(id, task_id, ts, kind, retry_count, payload) "
                "VALUES (:id, :task, now(), :kind, 0, '{}')"
            ),
            {"id": str(uuid.uuid4()), "task": str(task_id), "kind": kind},
        )
        session.commit()
    finally:
        session.close()


def _read_events_from(lines, count):
    """Parse SSE frames from a shared line iterator (streams read once)."""
    events = []
    frame = {}
    for line in lines:
        if not line:
            if "data" in frame:
                events.append(frame)
                if len(events) == count:
                    return events
            frame = {}
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        frame[field.strip()] = value.strip()
    return events


def _read_events(response, count):
    """Parse SSE frames until `count` data events arrive."""
    return _read_events_from(response.iter_lines(), count)


def test_backfill_replays_in_order(server_url, task_rows):
    """History first, framed as SSE with the gapless id."""
    task_id, seqs = task_rows
    with httpx.stream("GET", f"{server_url}/api/tasks/{task_id}/events", timeout=10) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _read_events(response, 3)
    assert [event["event"] for event in events] == ["audit"] * 3
    assert [int(event["id"]) for event in events] == sorted(seqs)
    first = json.loads(events[0]["data"])
    assert first["kind"] == "run.start"
    assert first["seq"] == min(seqs)


def test_resume_via_last_event_id(server_url, task_rows):
    """Reconnects replay only what the client missed."""
    task_id, seqs = task_rows
    headers = {"Last-Event-ID": str(seqs[0])}
    with httpx.stream(
        "GET", f"{server_url}/api/tasks/{task_id}/events", headers=headers, timeout=10
    ) as response:
        events = _read_events(response, 2)
    assert [int(event["id"]) for event in events] == sorted(seqs)[1:]


def test_live_event_arrives_in_order(server_url, task_rows):
    """A row committed mid-stream lands on the open connection."""
    task_id, seqs = task_rows
    with httpx.stream("GET", f"{server_url}/api/tasks/{task_id}/events", timeout=15) as response:
        lines = response.iter_lines()
        events = _read_events_from(lines, 3)
        assert len(events) == 3
        timer = threading.Timer(0.5, _insert_event, args=(task_id,))
        timer.start()
        try:
            live = _read_events_from(lines, 1)
        finally:
            timer.join()
    assert len(live) == 1
    assert int(live[0]["id"]) > max(seqs)
    assert json.loads(live[0]["data"])["kind"] == "tool.call"


def test_unknown_task_404s_without_opening_stream(server_url):
    """Unknown tasks 404 (the stream never opens)."""
    response = httpx.get(f"{server_url}/api/tasks/{uuid.uuid4()}/events", timeout=10)
    assert response.status_code == 404


def test_stream_needs_no_credentials(server_url, task_rows):
    """No auth headers, no cookies, no token in the handshake."""
    task_id, _ = task_rows
    with httpx.stream("GET", f"{server_url}/api/tasks/{task_id}/events", timeout=10) as response:
        assert response.status_code == 200
        assert "set-cookie" not in response.headers
        _read_events(response, 1)


class _Request:
    """Stub request: connected `stays` polls, then disconnects."""

    def __init__(self, stays=0):
        self._stays = stays

    async def is_disconnected(self) -> bool:
        if self._stays > 0:
            self._stays -= 1
            return False
        return True


def _session():
    return session_factory.session_for(session_factory.admin_engine())


def _row(**overrides):
    base = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "run_id": None,
        "seq": 7,
        "ts": "2026-10-05T00:00:00+00:00",
        "node": "policy_check",
        "tool": None,
        "kind": "policy.decision",
        "status": None,
        "error_type": None,
        "retry_count": 0,
        "duration_ms": None,
        "policy_result": "block",
        "verification_result": None,
        "payload": {"rule_id": "P-OWN-001"},
    }
    base.update(overrides)
    return AuditEventRead(**base)


def test_format_event_frames_id_event_data():
    """One frame: gapless id, named event, JSON data."""
    frame = format_event(_row()).decode()
    assert frame.startswith("id: 7\nevent: audit\ndata: ")
    assert json.loads(frame.split("data: ", 1)[1])["policy_result"] == "block"


async def test_generator_resume_filters_backfill(task_rows):
    """Rows at or below Last-Event-ID never replay."""
    task_id, seqs = task_rows
    session = _session()
    try:
        chunks = [
            chunk
            async for chunk in task_event_stream(task_id, sorted(seqs)[0], session, _Request())
        ]
    finally:
        session.close()
    assert len(chunks) == 2
    assert subscriber_count(str(task_id)) == 0


async def test_generator_unsubscribes_on_disconnect(task_rows):
    """The queue leaves the registry when the client goes away."""
    task_id, _ = task_rows
    session = _session()
    try:
        chunks = [chunk async for chunk in task_event_stream(task_id, 0, session, _Request())]
    finally:
        session.close()
    assert len(chunks) == 3
    assert subscriber_count(str(task_id)) == 0


async def test_generator_sends_heartbeat_while_waiting(task_rows):
    """Idle streams ping so proxies keep the connection."""
    task_id, _ = task_rows
    session = _session()
    try:
        gen = task_event_stream(task_id, 10**12, session, _Request(stays=2), heartbeat=0.01)
        chunks = [chunk async for chunk in gen]
    finally:
        session.close()
    assert chunks == [b": ping\n\n", b": ping\n\n"]
    assert subscriber_count(str(task_id)) == 0
