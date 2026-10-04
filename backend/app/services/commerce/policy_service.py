"""Policy read service."""

from sqlalchemy.orm import Session

from app.repositories.commerce.policy_repository import PolicyRepository
from app.schemas.commerce.policy import PolicyRead


class PolicyService:
    """Policy rule reads (thresholds for the worker's policy engine)."""

    def __init__(self, session: Session) -> None:
        self._repos = PolicyRepository(session)

    def list_all(self) -> list[PolicyRead]:
        """All policy rules."""
        return [
            PolicyRead(rule_key=p.rule_key, params=p.params, version=p.version)
            for p in self._repos.list_all()
        ]
