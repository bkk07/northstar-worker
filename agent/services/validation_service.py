"""Validation service: gate proposals, reserve accepted rows.

The node stays thin (and gate-clean): all repository access lives here.
Valid proposals reserve their `actions` row as `proposed`; Phase 16
moves the row to STARTED before executing. Invalid proposals return the
errors and a bumped failure count for the correction loop.
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from agent.contract.action_validator import TOOL_META, validate_action
from agent.contract.models import Contract
from agent.repositories.action_repository import ActionRepository
from northstar_common.tokens import canonical_params_hash


class ValidationService:
    """Proposal gate with journal reservation (`ns_runner` writes)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sessions = session_factory

    def check_and_reserve(
        self,
        run_id: str,
        action: dict,
        contract: Contract,
        validation_failures: int = 0,
    ) -> dict:
        """Validate; reserve the row or report errors with a new count."""
        outcome = validate_action(action, contract)
        if not outcome.valid:
            return {
                "validation_status": "invalid",
                "validation_error": "; ".join(outcome.errors),
                "validation_failures": validation_failures + 1,
            }
        meta = TOOL_META[action["tool"]]
        session = self._sessions()
        try:
            ActionRepository(session).reserve(
                UUID(run_id),
                meta.kind,
                action["tool"],
                action["params"],
                canonical_params_hash(action["params"]),
                meta.side_effect,
            )
            session.commit()
        finally:
            session.close()
        return {
            "validation_status": "ok",
            "validation_error": "",
            "validation_failures": 0,
        }
