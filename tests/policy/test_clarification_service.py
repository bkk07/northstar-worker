"""Agent clarification service: park, answer, and customer waits (Phase 22).

Live Postgres with throwaway task rows. The S4 arc runs through the
service: an ambiguous contract parks an operator clarification, the
answer comes back on resume, and the graph can re-enter the compiler.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from agent.ports.clock import SystemClock
from agent.services.clarification_service import ClarificationService
from database import session as session_factory
from database.models.worker.flow import Clarification
from database.models.worker.task import Task


@pytest.fixture()
def task_id():
    """Throwaway task row, cleaned up with its clarifications."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = Task(
        id=uuid.uuid4(),
        text="cancel my order",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase22-test",
    )
    session.add(task)
    session.commit()
    key = task.id
    session.close()
    try:
        yield key
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.query(Clarification).filter(Clarification.task_id == key).delete(
                synchronize_session=False
            )
            cleanup.query(Task).filter(Task.id == key).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()


def _service():
    sessions = lambda: session_factory.session_for(session_factory.admin_engine())  # noqa: E731
    return ClarificationService(sessions, SystemClock())


def _row(task_id):
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        return (
            session.query(Clarification)
            .filter(Clarification.task_id == task_id)
            .order_by(Clarification.created_at.desc())
            .first()
        )
    finally:
        session.close()


def test_operator_parks_with_deterministic_question(task_id):
    """First visit opens one pending operator request and parks."""
    outcome = _service().evaluate(str(task_id), "Operator input needed: scope?")
    assert outcome["clarification_status"] == "pending"
    assert "clarification_ref" in outcome
    assert "waiting_on_customer" not in outcome
    row = _row(task_id)
    assert row.kind == "operator" and row.status == "pending"


def test_second_visit_reuses_the_open_request(task_id):
    """No duplicate rows while the question is open."""
    service = _service()
    first = service.evaluate(str(task_id), "Operator input needed: scope?")
    second = service.evaluate(str(task_id), "Operator input needed: scope?")
    assert first["clarification_ref"] == second["clarification_ref"]


def test_answered_carries_the_answer_back(task_id):
    """Resume after the operator answers re-enters with the answer text."""
    service = _service()
    service.evaluate(str(task_id), "Operator input needed: scope?")
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        row = session.query(Clarification).filter(Clarification.task_id == task_id).first()
        row.status = "answered"
        row.answer = "cancel the mug, keep the jeans"
        row.answered_by = "operator"
        session.commit()
    finally:
        session.close()
    outcome = service.evaluate(str(task_id), "Operator input needed: scope?")
    assert outcome["clarification_status"] == "answered"
    assert outcome["clarification_ref"]["answer"] == "cancel the mug, keep the jeans"


def test_customer_kind_parks_on_the_customer(task_id):
    """Customer requests park distinctly until a reply or the TTL."""
    outcome = _service().evaluate(str(task_id), "Need the size?", kind="customer")
    assert outcome["clarification_status"] == "pending"
    assert outcome["waiting_on_customer"] is True
    assert _row(task_id).kind == "customer"


def test_customer_reply_answers(task_id):
    """An observed customer reply answers the request."""
    service = _service()
    service.evaluate(str(task_id), "Need the size?", kind="customer")
    outcome = service.evaluate(
        str(task_id), "Need the size?", kind="customer", customer_reply="Size 8"
    )
    assert outcome["clarification_status"] == "answered"
    assert outcome["clarification_ref"]["answered_by"] == "customer"


def test_customer_ttl_expires_the_wait(task_id):
    """The TTL bounds the customer wait (expired, never a guess)."""
    service = _service()
    service.evaluate(str(task_id), "Need the size?", kind="customer")
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        row = session.query(Clarification).filter(Clarification.task_id == task_id).first()
        row.created_at = datetime.now(UTC) - timedelta(hours=25)
        session.commit()
    finally:
        session.close()
    outcome = service.evaluate(str(task_id), "Need the size?", kind="customer")
    assert outcome["clarification_status"] == "expired"
