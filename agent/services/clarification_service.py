"""Agent clarification service: park on ambiguity, re-enter on answer.

The `clarification` node calls `evaluate` every visit. First visit opens
a pending request (operator kind by default) and parks. After the
operator answers, the resume visit carries the answer back so the graph
re-enters the contract compiler. Customer-kind requests park on the
customer: a reply observed through the read gateway answers them, and
the request TTL bounds the wait.
"""

from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from agent.ports.clock import ClockPort
from database.models.worker.flow import Clarification

PENDING = "pending"
ANSWERED = "answered"
EXPIRED = "expired"

OPERATOR = "operator"
CUSTOMER = "customer"


class ClarificationService:
    """Runner-role clarification requests (`worker.clarifications`)."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        clock: ClockPort,
    ) -> None:
        self._sessions = session_factory
        self._clock = clock

    def evaluate(
        self,
        task_id: str,
        question: str,
        kind: str = OPERATOR,
        customer_reply: str | None = None,
    ) -> dict:
        """Node outcome: park, answer, or carry the customer wait."""
        session = self._sessions()
        try:
            row = self._latest(session, task_id)
            if row is not None and row.status == ANSWERED:
                return {
                    "clarification_status": ANSWERED,
                    "clarification_ref": {
                        "id": str(row.id),
                        "answer": row.answer or "",
                        "answered_by": row.answered_by or "",
                    },
                }
            if row is not None and row.status == PENDING and row.kind == CUSTOMER:
                if customer_reply:
                    row.status = ANSWERED
                    row.answer = customer_reply
                    row.answered_by = "customer"
                    session.commit()
                    return {
                        "clarification_status": ANSWERED,
                        "clarification_ref": {
                            "id": str(row.id),
                            "answer": customer_reply,
                            "answered_by": "customer",
                        },
                    }
                if self._past_ttl(row):
                    row.status = EXPIRED
                    session.commit()
                    return {
                        "clarification_status": EXPIRED,
                        "clarification_ref": {"id": str(row.id)},
                    }
                session.commit()
                return {
                    "clarification_status": PENDING,
                    "clarification_ref": {"id": str(row.id)},
                    "waiting_on_customer": True,
                }
            if row is None or row.status != PENDING:
                row = self._open(session, task_id, question, kind)
            session.commit()
            outcome: dict = {
                "clarification_status": PENDING,
                "clarification_ref": {"id": str(row.id)},
            }
            if row.kind == CUSTOMER:
                outcome["waiting_on_customer"] = True
            return outcome
        finally:
            session.close()

    def _latest(self, session: Session, task_id: str) -> Clarification | None:
        """Newest clarification for the task (any status)."""
        return (
            session.query(Clarification)
            .filter(Clarification.task_id == UUID(task_id))
            .order_by(Clarification.created_at.desc())
            .first()
        )

    def _open(self, session: Session, task_id: str, question: str, kind: str) -> Clarification:
        """Open one pending request (operator answers in /worker)."""
        row = Clarification(
            task_id=UUID(task_id),
            kind=kind if kind in (OPERATOR, CUSTOMER) else OPERATOR,
            question=question,
            status=PENDING,
        )
        session.add(row)
        session.flush()
        return row

    def _past_ttl(self, row: Clarification) -> bool:
        """Customer waits end after the request TTL (24h from creation)."""
        return row.created_at <= self._clock.now() - timedelta(hours=24)
