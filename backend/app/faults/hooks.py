"""Fault injection hooks called by ops mutation services (Phase 9).

Bookkeeping runs on a PRIVATE connection (committed independently), so a
firing fault is consumed even when the mutation transaction rolls back —
otherwise a 500-before-commit would refire forever on retry.

- `before_mutation(target)`: match/count/consume a before-commit fault.
  Returns True when the service must skip its idempotency replay
  (DUPLICATE_EFFECT). May raise (500, 422, 401) or sleep (TIMEOUT).
- `after_mutation(target)`: match/count/consume an after-commit fault
  (the mutation row is already committed). May raise 500 or sleep.
"""

import time
from datetime import UTC, datetime

from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, UnauthorizedError, UnprocessableError
from app.faults.registry import BEFORE_TYPES, nth_call_of
from app.repositories.ops.session_repository import SessionRepository
from database.models.biz.ops import FaultPlan
from database.session import app_engine


class FaultHTTP500(AppError):
    """Fault-injected 500 (indistinguishable from a real one by design)."""

    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self) -> None:
        super().__init__("Internal Server Error (fault-injected)")


def _own_session() -> Session:
    """Private short-lived session (fault bookkeeping commits alone).

    expire_on_commit=False keeps rows readable after expunge: hooks hand
    detached plans to the service layer, which must not touch the DB
    through them.
    """
    return Session(bind=app_engine(), expire_on_commit=False)


def _match_and_bump(target: str, phase: str):
    """Find the armed plan for target+phase, bump its counter, and return it
    only when this call is its nth (else None). Commits independently.

    Phases split TIMEOUT by its `after_commit` param, so an after-commit
    timeout is never consumed by the before-commit hook.
    """
    after_timeout = and_(
        FaultPlan.fault_type == "TIMEOUT",
        FaultPlan.params["after_commit"].astext == "true",
    )
    if phase == "before":
        extra = and_(FaultPlan.fault_type.in_(BEFORE_TYPES), not_(after_timeout))
    else:
        extra = or_(
            FaultPlan.fault_type == "HTTP_500_AFTER_COMMIT",
            after_timeout,
        )
    session = _own_session()
    try:
        plan = (
            session.query(FaultPlan)
            .filter(
                FaultPlan.armed.is_(True),
                FaultPlan.consumed_at.is_(None),
                FaultPlan.target == target,
                extra,
            )
            .with_for_update()
            .first()
        )
        if plan is None:
            session.commit()
            return None
        plan.calls = (plan.calls or 0) + 1
        fires = plan.calls >= nth_call_of(plan.trigger or {})
        if fires:
            plan.armed = False
            plan.consumed_at = datetime.now(UTC)
        session.commit()
        session.expunge(plan)
        return plan if fires else None
    finally:
        session.close()


def before_mutation(target: str) -> bool:
    """Apply a before-commit fault. True = skip the idempotency replay."""
    plan = _match_and_bump(target, "before")
    if plan is None:
        return False
    fault_type = plan.fault_type
    params = plan.params or {}
    if fault_type == "SESSION_EXPIRY":
        _revoke_all_sessions()
        raise UnauthorizedError("ops session expired or invalid")
    if fault_type == "VALIDATION_ERROR":
        field = params.get("field", "request")
        message = params.get("message", f"{field} is invalid")
        raise UnprocessableError(f"validation failed: {message}")
    if fault_type == "DUPLICATE_EFFECT":
        return True
    if fault_type == "HTTP_500_BEFORE_COMMIT":
        raise FaultHTTP500()
    if fault_type == "TIMEOUT" and not params.get("after_commit", False):
        time.sleep(float(params.get("delay_seconds", 5)))
    return False


def after_mutation(target: str) -> None:
    """Apply an after-commit fault (the mutation row already exists)."""
    plan = _match_and_bump(target, "after")
    if plan is None:
        return
    fault_type = plan.fault_type
    params = plan.params or {}
    if fault_type == "HTTP_500_AFTER_COMMIT":
        raise FaultHTTP500()
    if fault_type == "TIMEOUT" and params.get("after_commit", False):
        time.sleep(float(params.get("delay_seconds", 5)))


def _revoke_all_sessions() -> None:
    """Revoke every live ops session (mid-run expiry chaos)."""
    from database.models.biz.ops import OpsSession

    session = _own_session()
    try:
        for row in session.query(OpsSession).filter(OpsSession.revoked.is_(False)).all():
            SessionRepository(session).revoke(row.id)
        session.commit()
    finally:
        session.close()


__all__ = ["FaultHTTP500", "after_mutation", "before_mutation"]
