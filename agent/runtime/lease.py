"""Task leases: one runner owns a task at a time (Phase 20).

Claim uses `SELECT … FOR UPDATE SKIP LOCKED` so parallel runners never
block each other — the loser simply finds nothing to claim. Heartbeats
extend ownership; an expired lease lets another runner start a new
`task_runs` attempt (crash resume in `resume.py`).
"""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, text

from database.models.worker.task import Task, TaskRun

LEASE_TTL_S = 60


class LeaseDenied(Exception):
    """Another live owner holds the task (or it is already terminal)."""


def claim(session, task_id: UUID, owner: str, now, ttl_s: int = LEASE_TTL_S) -> TaskRun:
    """Claim the next attempt row for a task (SKIP LOCKED, heartbeat set)."""
    from agent.runtime.transitions import assert_not_terminal
    from northstar_common.enums import TaskState

    task = session.get(Task, task_id)
    if task is None:
        raise LeaseDenied(f"unknown task: {task_id}")
    assert_not_terminal(TaskState(task.status))
    live = (
        session.query(TaskRun)
        .filter(
            TaskRun.task_id == task_id,
            TaskRun.ended_at.is_(None),
            TaskRun.lease_owner.is_not(None),
            TaskRun.lease_owner != owner,
            TaskRun.lease_expires_at > now,
        )
        .with_for_update(skip_locked=True)
        .first()
    )
    if live is not None:
        raise LeaseDenied(f"task {task_id} already leased by {live.lease_owner}")
    peak = session.scalar(
        select(TaskRun.attempt)
        .where(TaskRun.task_id == task_id)
        .order_by(TaskRun.attempt.desc())
        .limit(1)
    )
    run = TaskRun(
        task_id=task_id,
        attempt=(peak or 0) + 1,
        lease_owner=owner,
        lease_expires_at=now + timedelta(seconds=ttl_s),
        heartbeat_at=now,
        started_at=now,
    )
    session.add(run)
    session.flush()
    session.refresh(run)
    return run


def heartbeat(session, run_id: UUID, owner: str, now, ttl_s: int = LEASE_TTL_S) -> bool:
    """Extend a live owned lease (False when lost or finished)."""
    run = session.get(TaskRun, run_id)
    if run is None or run.ended_at is not None or run.lease_owner != owner:
        return False
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=ttl_s)
    session.flush()
    return True


def release(session, run_id: UUID, owner: str, now) -> None:
    """Give up the lease and stamp the run's end."""
    run = session.get(TaskRun, run_id)
    if run is None or run.lease_owner != owner:
        return
    run.lease_owner = None
    run.lease_expires_at = None
    run.ended_at = now
    session.flush()


def claimable_tasks(session, limit: int = 10) -> list[UUID]:
    """Pending/running tasks with no live lease (the poll loop reads this)."""
    rows = session.execute(
        text(
            "SELECT t.id FROM worker.tasks t "
            "WHERE t.status IN ('pending', 'running') "
            "AND NOT EXISTS (SELECT 1 FROM worker.task_runs r "
            "WHERE r.task_id = t.id AND r.ended_at IS NULL "
            "AND r.lease_expires_at > now()) "
            "ORDER BY t.created_at LIMIT :limit FOR UPDATE SKIP LOCKED"
        ),
        {"limit": limit},
    ).all()
    return [row[0] for row in rows]
