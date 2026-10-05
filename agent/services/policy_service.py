"""Policy service: evaluate, persist, and issue commit tokens.

`decide` is pure (contract + action + facts + date in, verdict out) so
the full rule table is unit-testable. `check_and_persist` adds the audit
row and, on ALLOW for a submit, the HMAC token the MCP guard verifies.
`pending_terminal_block` is the Phase 29 terminal gate: a minor submit
(note/status/reply) is refused before its first commit when any major
effect in the same contract (refund/replacement) would BLOCK — the task
is all-or-nothing against BLOCK, so the doomed run ends with zero
mutations instead of posting notes and failing closed afterwards.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from agent.contract.models import Contract
from agent.policy import authorization
from agent.policy.facts import Facts, gather_facts
from agent.policy.issuer import SUBMIT_ACTION, issue_submit_token
from agent.ports.clock import ClockPort
from agent.ports.tool_gateway import ToolGateway
from agent.repositories.action_repository import ActionRepository
from agent.repositories.policy_decision_repository import PolicyDecisionRepository
from northstar_common.tokens import canonical_params_hash

# Effects whose verdict decides the whole task (all-or-nothing vs BLOCK).
MAJOR_EFFECTS = frozenset({"refund.create", "replacement.create"})

# Ancillary effects that must not commit ahead of a doomed terminal.
MINOR_EFFECTS = frozenset({"ticket.note", "ticket.status", "ticket.reply"})

# Journal statuses proving a submit already mutated (gate skips those).
COMMITTED_STATUSES = frozenset({"done", "reconciled"})


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
        self.persist(task_id, run_id, action, result)
        return result

    def persist(self, task_id: str, run_id: str, action: dict, result: PolicyResult) -> None:
        """Append one policy-decision row (persistence without evaluation)."""
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

    def pending_terminal_block(
        self,
        task_id: str,
        run_id: str,
        action: dict,
        contract: Contract,
        gateway: ToolGateway,
    ) -> tuple[dict, PolicyResult] | None:
        """Prospective BLOCK for a minor submit ahead of a doomed major.

        Returns the synthetic major action plus its BLOCK verdict when any
        uncommitted major effect in the contract would BLOCK under freshly
        gathered facts (probes included, so P-DUP-001 fires here too).
        HUMAN_APPROVAL passes — approval flows keep their notes — and
        majors this run already committed are skipped, so post-commit
        notes still flow. None means the minor may be decided normally.
        """
        params = action.get("params", {}) if isinstance(action, dict) else {}
        if action.get("tool") != SUBMIT_ACTION or params.get("effect") not in MINOR_EFFECTS:
            return None
        majors = [e for e in contract.effects if e.effect in MAJOR_EFFECTS]
        if not majors:
            return None
        committed = self._committed_effects(run_id)
        for expected in majors:
            if expected.effect in committed:
                continue
            major = {
                "tool": SUBMIT_ACTION,
                "params": {"effect": expected.effect, **dict(expected.params)},
            }
            verdict = self.decide(contract, major, gather_facts(task_id, contract, major, gateway))
            if verdict.outcome == "block":
                return major, PolicyResult(
                    outcome="block",
                    rule_id=verdict.rule_id,
                    reason=f"terminal {expected.effect} would block: {verdict.reason}",
                )
        return None

    def _committed_effects(self, run_id: str) -> set[str]:
        """Major effects this run already mutated (journal statuses)."""
        session = self._sessions()
        try:
            rows = ActionRepository(session).list_by_run(UUID(run_id))
        finally:
            session.close()
        return {
            row.params.get("effect", "")
            for row in rows
            if row.tool == SUBMIT_ACTION
            and row.status in COMMITTED_STATUSES
            and isinstance(row.params, dict)
        }

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
