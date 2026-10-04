"""Checkpoint repository + store round-trip on live Postgres (Phase 12).

Proves the resume cache the runner depends on: rows append in order and
`latest` returns the tip. Uses throwaway task/run UUIDs, cleaned up after.
"""

import uuid

from agent.graph.checkpointer import InMemoryCheckpointStore, PostgresCheckpointStore
from agent.repositories.checkpoint_repository import CheckpointRepository
from database import session as session_factory
from database.models.worker.task import Task, TaskCheckpoint, TaskRun


def _task_and_run(session):
    task = Task(
        id=uuid.uuid4(),
        text="checkpoint probe",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase12-test",
    )
    run = TaskRun(id=uuid.uuid4(), task_id=task.id, attempt=1)
    session.add_all([task, run])
    session.commit()
    return task, run


def test_repository_appends_in_order():
    """save assigns gapless seq; latest returns the tip."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = run = None
    try:
        task, run = _task_and_run(session)
        repo = CheckpointRepository(session)
        first = repo.save(run.id, "understand", {"cursor": 0})
        second = repo.save(run.id, "contract", {"cursor": 1})
        assert (first.seq, second.seq) == (0, 1)
        tip = repo.latest(run.id)
        assert tip is not None and tip.node == "contract"
        assert [row.node for row in repo.history(run.id)] == ["understand", "contract"]
        session.commit()
    finally:
        session.rollback()
        session.query(TaskCheckpoint).filter(TaskCheckpoint.run_id == run.id).delete(
            synchronize_session=False
        )
        session.query(TaskRun).filter(TaskRun.id == run.id).delete(synchronize_session=False)
        session.query(Task).filter(Task.id == task.id).delete(synchronize_session=False)
        session.commit()
        session.close()


def test_in_memory_store_round_trip():
    """The test/CI store behaves like the Postgres one (seq + tip)."""
    store = InMemoryCheckpointStore()
    assert store.latest("r1") is None
    store.save("r1", "understand", {"a": 1})
    tip = store.save("r1", "contract", {"a": 2})
    assert tip.seq == 1
    assert store.latest("r1") is not None
    assert store.latest("r1").node == "contract"


def test_postgres_store_round_trip():
    """Store over a real session factory persists across instances."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = run = None
    try:
        task, run = _task_and_run(session)
        session.close()
        run_key = str(run.id)
        store = PostgresCheckpointStore(lambda: session_factory.session_for(engine))
        store.save(run_key, "understand", {"cursor": 0})
        tip = PostgresCheckpointStore(lambda: session_factory.session_for(engine)).latest(run_key)
        assert tip is not None and tip.node == "understand" and tip.seq == 0
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.query(TaskCheckpoint).filter(TaskCheckpoint.run_id == run.id).delete(
                synchronize_session=False
            )
            cleanup.query(TaskRun).filter(TaskRun.id == run.id).delete(synchronize_session=False)
            cleanup.query(Task).filter(Task.id == task.id).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()
