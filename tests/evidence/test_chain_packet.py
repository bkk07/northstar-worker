"""Audit chain replay + terminal packet persistence (Phase 24, live DB).

A stub graph ends one run BLOCKED through the real runner: the packet
lands in `worker.evidence`, the `run.packet` audit cites its headline,
and the node chain replays from audit events alone.
"""

import pytest
from sqlalchemy import text

from agent.evidence.builder import reconstruct_chain
from agent.ports.clock import SystemClock
from agent.repositories.audit_repository import AuditRepository
from agent.repositories.task_repository import TaskRepository
from agent.runtime.audit_emitter import AuditEmitter
from agent.runtime.runner import Runner
from database import session as session_factory
from database.models.worker.evidence import Evidence


@pytest.fixture()
def task_id():
    """Throwaway pending task with full cleanup (evidence included)."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = TaskRepository(session).create_task("refund Rs. 100,000", "explicit", "phase24-e2e")
    session.commit()
    key = task.id
    session.close()
    try:
        yield key
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text("DELETE FROM worker.evidence WHERE task_id = :id"), {"id": str(key)}
            )
            cleanup.execute(
                text(
                    "DELETE FROM worker.task_checkpoints WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = :id)"
                ),
                {"id": str(key)},
            )
            cleanup.execute(
                text("DELETE FROM worker.audit_events WHERE task_id = :id"),
                {"id": str(key)},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_runs WHERE task_id = :id"), {"id": str(key)}
            )
            cleanup.execute(text("DELETE FROM worker.tasks WHERE id = :id"), {"id": str(key)})
            cleanup.commit()
        finally:
            cleanup.close()


def _sessions():
    return session_factory.session_for(session_factory.admin_engine())


class _BlockedGraph:
    """One node: the run ends BLOCKED on an ownership rule."""

    def stream(self, state, config=None, stream_mode=None):
        """Yield the terminal delta, then end."""
        _ = (config, stream_mode)
        yield {
            "finalize": {
                "status": "blocked",
                "policy_decision": {
                    "outcome": "block",
                    "rule_id": "P-OWN-001",
                    "reason": "not your order",
                },
            }
        }


def test_terminal_run_persists_packet_and_replays(task_id):
    """BLOCKED ends with a packet, a run.packet audit, and a replayable chain."""
    merged = Runner(_sessions, SystemClock(), graph=_BlockedGraph()).run_task(str(task_id))
    assert merged["status"] == "blocked"
    assert merged["evidence_ref"]["summary"][0].startswith("BLOCKED")

    session = _sessions()
    try:
        packet_row = (
            session.query(Evidence)
            .filter(Evidence.task_id == task_id, Evidence.packet["type"].astext == "packet/v1")
            .one()
        )
        assert packet_row.packet["status"] == "blocked"
        assert packet_row.packet["policy"]["decision"]["rule_id"] == "P-OWN-001"
        assert packet_row.summary.splitlines()[0].startswith("BLOCKED")

        events = AuditRepository(session).list_by_task(task_id)
        kinds = [event.kind for event in events]
        assert kinds[0] == "run.start"
        assert "run.packet" in kinds
        assert kinds.index("run.packet") > kinds.index("run.end")
        chain = reconstruct_chain(
            [
                {"seq": event.seq, "id": str(event.id), "kind": event.kind, "node": event.node}
                for event in events
            ]
        )
        assert chain == ["finalize"]
        payloads = [event.payload for event in events if event.kind == "node.transition"]
        assert payloads and payloads[0]["delta_keys"] == ["policy_decision", "status"]
    finally:
        session.close()


def test_emitted_chain_replays_in_seq_order(task_id):
    """Out-of-order reads still replay the emission order."""
    emitter = AuditEmitter(_sessions, SystemClock())
    for node in ("understand", "contract", "policy_check"):
        emitter.node_transition(str(task_id), None, node, status="", payload={"delta_keys": []})
    session = _sessions()
    try:
        events = AuditRepository(session).list_by_task(task_id)
        assert [event.seq for event in events] == sorted(event.seq for event in events)
        assert reconstruct_chain(
            [
                {"seq": event.seq, "id": str(event.id), "kind": event.kind, "node": event.node}
                for event in events
            ]
        ) == ["understand", "contract", "policy_check"]
    finally:
        session.close()
