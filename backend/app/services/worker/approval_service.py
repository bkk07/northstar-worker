"""Worker approval service: decide held commits, requeue parked tasks.

Approvals are single-use and bound to (task, action, params hash); they
expire at `max_approval_wait`. Approve/reject moves the task back to
`running` so the runner resumes at `human_approval`: approved consumes
into a commit token, rejected finalizes BLOCKED with no mutation.
Overdue approvals expire lazily on every read path (the expiry sweep).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.worker.approvals import ApprovalDecide, ApprovalRead
from database.models.worker.flow import Approval
from database.models.worker.task import Task

# Mirror of the agent's allowed WAITING -> RUNNING requeue (the runner's
# claim loop picks up `running` tasks with no live lease).
_REQUEUE_FROM = frozenset({"waiting_for_approval"})

APPROVAL_WAIT_S = 24 * 3600


class ApprovalService:
    """Operator approval queue over `worker.approvals` (`ns_app` role)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_pending(self) -> list[ApprovalRead]:
        """Pending approvals, oldest first (overdue ones expire first)."""
        self.expire_overdue()
        rows = (
            self._session.query(Approval)
            .filter(Approval.status == "pending")
            .order_by(Approval.created_at)
            .all()
        )
        return [self._to_dto(row) for row in rows]

    def get_approval(self, approval_id: UUID) -> ApprovalRead:
        """One approval (404 when absent; overdue reads as expired)."""
        self.expire_overdue()
        return self._to_dto(self._get(approval_id))

    def approve(self, approval_id: UUID, payload: ApprovalDecide) -> ApprovalRead:
        """Approve once and requeue the task (409 unless pending)."""
        self.expire_overdue()
        row = self._get(approval_id)
        if row.status != "pending":
            raise ConflictError(f"approval {approval_id} is already {row.status}")
        row.status = "approved"
        row.approver = payload.approver
        row.resolved_at = datetime.now(UTC)
        self._requeue(row.task_id)
        self._session.commit()
        self._session.refresh(row)
        return self._to_dto(row)

    def reject(self, approval_id: UUID, payload: ApprovalDecide) -> ApprovalRead:
        """Reject once and requeue the task (the graph finalizes BLOCKED)."""
        self.expire_overdue()
        row = self._get(approval_id)
        if row.status != "pending":
            raise ConflictError(f"approval {approval_id} is already {row.status}")
        row.status = "rejected"
        row.approver = payload.approver
        row.resolved_at = datetime.now(UTC)
        self._requeue(row.task_id)
        self._session.commit()
        self._session.refresh(row)
        return self._to_dto(row)

    def expire_overdue(self) -> int:
        """Flip overdue pending approvals to expired (the expiry sweep)."""
        now = datetime.now(UTC)
        rows = (
            self._session.query(Approval)
            .filter(Approval.status == "pending", Approval.expires_at <= now)
            .all()
        )
        for row in rows:
            row.status = "expired"
            row.resolved_at = now
            self._requeue(row.task_id, silent=True)
        if rows:
            self._session.commit()
        return len(rows)

    def _get(self, approval_id: UUID) -> Approval:
        row = self._session.get(Approval, approval_id)
        if row is None:
            raise NotFoundError(f"approval {approval_id} not found")
        return row

    def _requeue(self, task_id: UUID, silent: bool = False) -> None:
        """Parked task back to `running` (the claim loop resumes it)."""
        task = self._session.get(Task, task_id)
        if task is None:
            if silent:
                return
            raise NotFoundError(f"task {task_id} not found")
        if task.status in _REQUEUE_FROM:
            task.status = "running"
            task.current_state = "running"

    @staticmethod
    def _to_dto(row: Approval) -> ApprovalRead:
        return ApprovalRead(
            id=row.id,
            task_id=row.task_id,
            requested_action=row.requested_action,
            params=dict(row.params or {}),
            params_hash=row.params_hash,
            reason=row.reason,
            policy_rule_id=row.policy_rule_id,
            status=row.status,
            approver=row.approver,
            resolved_at=row.resolved_at,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )


def default_expiry(now: datetime | None = None) -> datetime:
    """Approval deadline: `max_approval_wait` (24h) after the request."""
    return (now or datetime.now(UTC)) + timedelta(seconds=APPROVAL_WAIT_S)
