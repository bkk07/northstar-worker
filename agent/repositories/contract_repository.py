"""Contract repository: validated work orders (`worker.task_contracts`).

One row per compilation; the newest row per task is the locked contract.
Nodes never import this package directly; `ContractService` does
(architecture gate).
"""

from uuid import UUID

from sqlalchemy import select

from agent.contract.models import Contract
from agent.repositories.base import BaseRepository
from database.models.worker.task import TaskContract


class ContractRepository(BaseRepository[TaskContract]):
    """`ns_runner`-role persistence for task contracts."""

    def save(self, contract: Contract) -> TaskContract:
        """Insert one compiled contract (status + ambiguity columns set)."""
        row = TaskContract(
            task_id=UUID(contract.task_id),
            contract=contract.model_dump(),
            status=contract.status,
            ambiguity={"items": list(contract.ambiguity)},
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def latest_by_task(self, task_id: UUID) -> TaskContract | None:
        """Newest contract for a task (the locked one)."""
        return self._session.scalar(
            select(TaskContract)
            .where(TaskContract.task_id == task_id)
            .order_by(TaskContract.created_at.desc())
            .limit(1)
        )
