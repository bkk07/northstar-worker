"""Policy decision repository: audit rows (`worker.policy_decisions`).

Every evaluation writes one row (rule, task, run, action, params,
outcome, reason, timestamp). Nodes never import this package directly;
`PolicyService` does (architecture gate).
"""

from uuid import UUID

from sqlalchemy import select

from agent.policy.authorization import Decision
from agent.repositories.base import BaseRepository
from database.models.worker.flow import PolicyDecision


class PolicyDecisionRepository(BaseRepository[PolicyDecision]):
    """`ns_runner`-role persistence for policy evaluations."""

    def save(
        self,
        task_id: UUID,
        run_id: UUID | None,
        action_id: UUID | None,
        decision: Decision,
        params: dict,
        at,
    ) -> PolicyDecision:
        """Insert one decision row (append-only audit)."""
        row = PolicyDecision(
            task_id=task_id,
            run_id=run_id,
            action_id=action_id,
            rule_id=decision.rule_id,
            outcome=decision.outcome,
            reason=decision.reason,
            params=params,
            ts=at,
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def list_by_run(self, run_id: UUID) -> list[PolicyDecision]:
        """All decisions for a run, oldest first."""
        return list(
            self._session.scalars(
                select(PolicyDecision)
                .where(PolicyDecision.run_id == run_id)
                .order_by(PolicyDecision.ts)
            ).all()
        )
