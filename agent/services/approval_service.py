"""Agent approval service: park on HUMAN_APPROVAL, consume on resume.

The `human_approval` node calls `evaluate` every visit. First visit
creates the pending request (bound to task/action/params hash, expiring
in 24h) and parks. After the operator approves, the resume visit finds
the approved row, consumes it single-use, and issues the submit token —
changed params or an expired/replayed approval never yields a token.
"""

from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from agent.policy.issuer import issue_submit_token, signable_params
from agent.ports.clock import ClockPort
from database.models.worker.flow import Approval
from northstar_common.tokens import canonical_params_hash

APPROVAL_WAIT_S = 24 * 3600

PENDING = "pending"
APPROVED = "approved"
CONSUMED = "consumed"
REJECTED = "rejected"
EXPIRED = "expired"


class ApprovalService:
    """Runner-role approval requests (`worker.approvals`)."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        secret: str,
        clock: ClockPort,
    ) -> None:
        self._sessions = session_factory
        self._secret = secret
        self._clock = clock

    def evaluate(self, task_id: str, run_id: str, action: dict, decision: dict) -> dict:
        """Node outcome: park, resume with token, or carry the terminal."""
        session = self._sessions()
        try:
            self._expire_overdue(session)
            wanted = _params_hash(action)
            terminal = self._latest_terminal(session, task_id, action, wanted)
            if terminal is not None:
                session.commit()
                return terminal
            approved = self._consume(session, task_id, action, wanted)
            if approved is not None:
                token = issue_submit_token(self._secret, task_id, action.get("params", {}))
                session.commit()
                return {
                    "approval_status": APPROVED,
                    "approval_ref": {"id": str(approved.id)},
                    "last_action": {
                        **action,
                        "params": {**action.get("params", {}), "token": token},
                    },
                }
            ref = self._ensure_pending(session, task_id, run_id, action, wanted, decision)
            session.commit()
            return {
                "approval_status": PENDING,
                "approval_ref": {"id": str(ref.id)},
            }
        finally:
            session.close()

    def _latest_terminal(
        self, session: Session, task_id: str, action: dict, wanted: str
    ) -> dict | None:
        """Rejected/expired/consumed rows for this action hash end the wait."""
        rows = self._for_action(session, task_id, action, wanted)
        for row in rows:
            if row.status == REJECTED:
                return {
                    "approval_status": REJECTED,
                    "approval_ref": {"id": str(row.id)},
                }
            if row.status == EXPIRED:
                return {
                    "approval_status": EXPIRED,
                    "approval_ref": {"id": str(row.id)},
                }
        return None

    def _consume(
        self, session: Session, task_id: str, action: dict, wanted: str
    ) -> Approval | None:
        """Single-use: flip one approved row to consumed (None when absent)."""
        row = (
            session.query(Approval)
            .filter(
                Approval.task_id == UUID(task_id),
                Approval.requested_action == action.get("tool", ""),
                Approval.params_hash == wanted,
                Approval.status == APPROVED,
            )
            .order_by(Approval.created_at.desc())
            .first()
        )
        if row is None:
            return None
        row.status = CONSUMED
        row.resolved_at = self._clock.now()
        return row

    def _ensure_pending(
        self,
        session: Session,
        task_id: str,
        run_id: str,
        action: dict,
        wanted: str,
        decision: dict,
    ) -> Approval:
        """Reuse the open request for this hash, else open one."""
        row = (
            session.query(Approval)
            .filter(
                Approval.task_id == UUID(task_id),
                Approval.requested_action == action.get("tool", ""),
                Approval.params_hash == wanted,
                Approval.status == PENDING,
            )
            .order_by(Approval.created_at.desc())
            .first()
        )
        if row is not None:
            return row
        now = self._clock.now()
        row = Approval(
            task_id=UUID(task_id),
            run_id=UUID(run_id) if run_id else None,
            requested_action=action.get("tool", ""),
            params=dict(action.get("params", {})),
            params_hash=wanted,
            reason=decision.get("reason", ""),
            policy_rule_id=decision.get("rule_id", ""),
            status=PENDING,
            expires_at=now + timedelta(seconds=APPROVAL_WAIT_S),
        )
        session.add(row)
        session.flush()
        return row

    def _for_action(
        self, session: Session, task_id: str, action: dict, wanted: str
    ) -> list[Approval]:
        """All requests for this action hash, newest first."""
        return (
            session.query(Approval)
            .filter(
                Approval.task_id == UUID(task_id),
                Approval.requested_action == action.get("tool", ""),
                Approval.params_hash == wanted,
            )
            .order_by(Approval.created_at.desc())
            .all()
        )

    def _expire_overdue(self, session: Session) -> int:
        """Flip overdue pending rows to expired (returns the count)."""
        now = self._clock.now()
        rows = (
            session.query(Approval)
            .filter(Approval.status == PENDING, Approval.expires_at <= now)
            .all()
        )
        for row in rows:
            row.status = EXPIRED
            row.resolved_at = now
        return len(rows)


def _params_hash(action: dict) -> str:
    """Approval binding: the signed payload hash (stable across retries)."""
    return canonical_params_hash(signable_params(action.get("params", {})))
