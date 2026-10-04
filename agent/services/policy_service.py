"""Policy service: evaluate, persist, and issue commit tokens.

`decide` is pure (contract + action + facts + date in, verdict out) so
the full rule table is unit-testable. `check_and_persist` adds the audit
row and, on ALLOW for a submit, the HMAC token the MCP guard verifies.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from agent.contract.models import Contract
from agent.policy import authorization
from agent.policy.facts import Facts
from agent.policy.issuer import SUBMIT_ACTION, issue_submit_token
from agent.ports.clock import ClockPort
from agent.repositories.action_repository import ActionRepository
from agent.repositories.policy_decision_repository import PolicyDecisionRepository
from northstar_common.tokens import canonical_params_hash


@dataclass(frozen=True)
class PolicyResult:
    """Verdict plus the commit token when one is owed."""

    outcome: str
    rule_id: str
    reason: str
    token: str = ""


class PolicyService:
    """Deterministic eligibility + authorization (`ns_runner` audit)."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        secret: str,
        clock: ClockPort,
    ) -> None:
        self._sessions = session_factory
        self._secret = secret
        self._clock = clock

    def decide(self, contract: Contract, action: dict, facts: Facts) -> PolicyResult:
        """Pure evaluation (no persistence, no token side effects)."""
        today = self._clock.now().date()
        verdict = authorization.evaluate(contract, action, facts, today)
        token = ""
        if verdict.outcome == "allow" and action.get("tool") == SUBMIT_ACTION:
            token = issue_submit_token(self._secret, contract.task_id, action.get("params", {}))
        return PolicyResult(
            outcome=verdict.outcome,
            rule_id=verdict.rule_id,
            reason=verdict.reason,
            token=token,
        )

    def check_and_persist(
        self,
        task_id: str,
        run_id: str,
        action: dict,
        contract: Contract,
        facts: Facts,
    ) -> PolicyResult:
        """Evaluate, append the audit row (best-effort action link), return."""
        result = self.decide(contract, action, facts)
        session = self._sessions()
        try:
            action_id = self._link_action(session, run_id, action)
            PolicyDecisionRepository(session).save(
                UUID(task_id),
                UUID(run_id),
                action_id,
                authorization.Decision(
                    outcome=result.outcome,
                    rule_id=result.rule_id,
                    reason=result.reason,
                ),
                action.get("params", {}),
                self._clock.now(),
            )
            session.commit()
        finally:
            session.close()
        return result

    def _link_action(self, session: Session, run_id: str, action: dict) -> UUID | None:
        """Latest reserved row matching tool + params hash (None when absent)."""
        try:
            wanted = canonical_params_hash(action.get("params", {}))
        except Exception:
            return None
        rows = ActionRepository(session).list_by_run(UUID(run_id))
        for row in reversed(rows):
            if row.tool == action.get("tool") and row.params_hash == wanted:
                return row.id
        return None
