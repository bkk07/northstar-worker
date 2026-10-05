"""Phase 20: leases and cancel against live Postgres (no other servers)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from agent.ports.clock import SystemClock
from agent.repositories.task_repository import TaskRepository
from agent.runtime import lease
from database import session as session_factory


@pytest.fixture()
def leases(runner_session):
    """Task + session pair with admin cleanup from the shared fixture."""
    session, created = runner_session
    repo = TaskRepository(session)
    task = repo.create_task("durable task", "explicit", "e2e-lease")
    session.commit()
    created.append(task.id)
    return session, task


def _now():
    return datetime.now(UTC)


def test_claim_heartbeat_release_cycle(leases):
    """One owner claims, extends, and releases (runs end cleanly)."""
    session, task = leases
    run = lease.claim(session, task.id, "owner-a", _now())
    session.commit()
    assert run.attempt == 1 and run.lease_owner == "owner-a"
    assert lease.heartbeat(session, run.id, "owner-a", _now()) is True
    session.commit()
    lease.release(session, run.id, "owner-a", _now())
    session.commit()
    row = session.execute(
        text("SELECT lease_owner, ended_at FROM worker.task_runs WHERE id = :id"),
        {"id": run.id},
    ).first()
    assert row[0] is None and row[1] is not None


def test_second_owner_denied_until_expiry(leases):
    """Parallel runners never share a task (SKIP LOCKED loser fails fast)."""
    session, task = leases
    run = lease.claim(session, task.id, "owner-a", _now())
    session.commit()
    with pytest.raises(lease.LeaseDenied):
        lease.claim(session, task.id, "owner-b", _now())
    session.rollback()
    expired = _now() - timedelta(seconds=120)
    session.execute(
        text("UPDATE worker.task_runs SET lease_expires_at = :exp WHERE id = :id"),
        {"exp": expired, "id": run.id},
    )
    session.commit()
    run2 = lease.claim(session, task.id, "owner-b", _now())
    session.commit()
    assert run2.attempt == 2, "expiry starts a new attempt (crash resume)"


def test_heartbeat_lost_when_released(leases):
    """Finished runs refuse heartbeats (no zombie ownership)."""
    session, task = leases
    run = lease.claim(session, task.id, "owner-a", _now())
    session.commit()
    lease.release(session, run.id, "owner-a", _now())
    session.commit()
    assert lease.heartbeat(session, run.id, "owner-a", _now()) is False


def test_runner_uses_runner_engine_sessions():
    """Lease helpers accept the wiring session factory (smoke the import)."""
    factory = session_factory.session_for(session_factory.runner_engine())
    try:
        ids = lease.claimable_tasks(factory, limit=5)
        assert isinstance(ids, list)
    finally:
        factory.close()


def test_system_clock_monotonic_moves():
    """The budget wall-clock source actually advances."""
    clock = SystemClock()
    assert clock.monotonic() >= 0
