"""Phase 29: two-runner ticket flood (live Postgres, no LLM, no browser).

Two runners race the same ticket refund: exactly one owns the lease,
exactly one commit reaches the tools, and the loser adopts instead of
duplicating. The gateway is a recording fake; the lease claims, the
journal rows, the probe adoption, and the commit count are all real.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from agent.ports.clock import SystemClock
from agent.runtime import lease
from agent.services.execution_service import ExecutionService
from database import session as session_factory
from database.models.worker.task import Task


def _now():
    return datetime.now(UTC)


@pytest.fixture()
def flooded():
    """One task row, cleaned with every journal row afterwards."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = Task(
        id=uuid.uuid4(),
        text="flood the refund",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase29-flood",
    )
    session.add(task)
    session.commit()
    task_id = task.id
    session.close()
    try:
        yield task_id
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text(
                    "DELETE FROM worker.action_attempts WHERE action_id IN "
                    "(SELECT id FROM worker.actions WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = :task))"
                ),
                {"task": task_id},
            )
            cleanup.execute(
                text(
                    "DELETE FROM worker.actions WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = :task)"
                ),
                {"task": task_id},
            )
            cleanup.execute(
                text("DELETE FROM worker.policy_decisions WHERE task_id = :task"),
                {"task": task_id},
            )
            cleanup.execute(
                text("DELETE FROM worker.audit_events WHERE task_id = :task"),
                {"task": task_id},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_runs WHERE task_id = :task"), {"task": task_id}
            )
            cleanup.execute(text("DELETE FROM worker.tasks WHERE id = :task"), {"task": task_id})
            cleanup.commit()
        finally:
            cleanup.close()


class FloodGateway:
    """Recording tools: one commit wins, probes see it afterwards."""

    def __init__(self):
        self.commits = []
        self._lock = threading.Lock()

    def inspect_state(self, task_id, kind, key, extra=None):
        """The refund probe turns found once the first commit lands."""
        with self._lock:
            if kind == "refund" and self.commits:
                return {"found": True, "kind": "refund", "entity_id": "refund-1"}
        return {"found": False}

    def browser_submit(self, task_id, ref, mutation_key, token, params):
        """Record exactly-once (the real MCP guard would reject replays)."""
        with self._lock:
            self.commits.append(dict(params))
        return {"ok": True, "entity_id": "refund-1"}


def _claim(task_id, owner, results):
    session = session_factory.session_for(session_factory.runner_engine())
    try:
        try:
            run = lease.claim(session, task_id, owner, _now())
            session.commit()
            results[owner] = str(run.id)
        except Exception as exc:  # LeaseDenied: the loser fails fast
            session.rollback()
            results[owner] = type(exc).__name__
    finally:
        session.close()


def test_only_one_runner_owns_the_task(flooded):
    """Concurrent claims converge: one owner, one LeaseDenied."""
    results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        pool.submit(_claim, flooded, "runner-a", results)
        pool.submit(_claim, flooded, "runner-b", results)
    assert sorted(results) == ["runner-a", "runner-b"]
    assert sum(1 for value in results.values() if value == "LeaseDenied") == 1
    assert sum(1 for value in results.values() if "Denied" not in value) == 1


def _submit_params():
    return {
        "effect": "refund.create",
        "ref": "flood",
        "order_id": "o-1943",
        "ticket_id": "t-102",
        "amount_paise": 250000,
    }


def test_loser_adopts_instead_of_duplicating(flooded):
    """Both runners pass policy; the second adopts (one gateway commit)."""
    gateway = FloodGateway()
    task_key = str(flooded)
    engine = session_factory.runner_engine()
    session = session_factory.session_for(engine)
    try:
        run_a = lease.claim(session, flooded, "runner-a", _now())
        session.commit()
        run_a_id = str(run_a.id)
    finally:
        session.close()

    service = ExecutionService(
        lambda: session_factory.session_for(session_factory.runner_engine()),
        gateway,
        SystemClock(),
    )
    action = {"tool": "browser_submit", "params": _submit_params()}
    first = service.execute(task_key, run_a_id, action)
    assert first.ok and first.mutated is True

    session2 = session_factory.session_for(engine)
    try:
        lease.release(session2, run_a.id, "runner-a", _now())
        session2.commit()
        run_b = lease.claim(session2, flooded, "runner-b", _now())
        session2.commit()
        run_b_id = str(run_b.id)
    finally:
        session2.close()

    second = service.execute(task_key, run_b_id, action)
    assert second.ok
    assert len(gateway.commits) == 1, "exactly one tool commit"
    assert second.mutated is False and second.payload.get("reconciled") is True


def test_mutation_keys_match_across_runs(flooded):
    """Same task + params give the same key: replays are recognizable."""
    from agent.runtime import mutation_keys

    params = _submit_params()
    task_key = str(flooded)
    assert mutation_keys.key_for(task_key, "browser_submit", params) == mutation_keys.key_for(
        task_key, "browser_submit", dict(params)
    )
    assert mutation_keys.key_for(
        task_key, "browser_submit", {**params, "ref": "other-ref"}
    ) == mutation_keys.key_for(task_key, "browser_submit", params)
