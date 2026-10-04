"""Decision service: the single next typed action.

Inputs are the plan cursor, working memory, the last observation, and
the validator's last error. After `MAX_VALIDATION_ROUNDS` failed
corrections the service stops spending LLM calls and emits a harmless
`browser_observe` — the feedback loop always terminates, and the
observation unblocks the next real decision.
"""

from agent.contract.models import Contract
from agent.llm.client import MercuryClient
from agent.llm.prompts import get_prompt
from agent.llm.schemas import NextAction
from northstar_common.errors import NorthstarError

MAX_VALIDATION_ROUNDS = 3


class DecisionError(NorthstarError):
    """The action proposal was unusable (not a runtime retry)."""

    code = "DECISION_ERROR"


class DecisionService:
    """Mercury-backed next-action choice with a bounded correction loop."""

    def __init__(self, llm: MercuryClient, max_rounds: int = MAX_VALIDATION_ROUNDS) -> None:
        self._llm = llm
        self._max_rounds = max_rounds

    def next_action(
        self,
        contract: Contract,
        plan: list[dict],
        cursor: int,
        memory: list[dict],
        last_observation: dict,
        validation_error: str = "",
        validation_failures: int = 0,
    ) -> NextAction:
        """Propose the next action, or a safe observe when corrections run out."""
        if validation_failures >= self._max_rounds:
            return NextAction(
                tool="browser_observe",
                params={},
                rationale=("validation fallback: corrections exhausted, re-observing to unblock"),
            )
        user = _decision_brief(contract, plan, cursor, memory, last_observation, validation_error)
        try:
            return self._llm.propose(NextAction, get_prompt("decide"), user)
        except NorthstarError as exc:
            raise DecisionError(f"action proposal failed: {exc}") from None


def _decision_brief(
    contract: Contract,
    plan: list[dict],
    cursor: int,
    memory: list[dict],
    last_observation: dict,
    validation_error: str,
) -> str:
    """Ground the decider: plan position, memory, observation, last error."""
    upcoming = plan[cursor : cursor + 3]
    lines = [
        f"Goal: {contract.goal}",
        f"Plan step {cursor + 1} of {len(plan)}:",
        *(f"- {step.get('step', '')} [{step.get('tool', '')}]" for step in upcoming),
        f"Capabilities: {', '.join(contract.capabilities)}",
        f"Memory: {memory if memory else 'none yet'}",
        f"Last observation: {last_observation if last_observation else 'none yet'}",
    ]
    if validation_error:
        lines.append(
            "Correction: your previous proposal was rejected "
            f"({validation_error}). Fix exactly that and nothing else."
        )
    return "\n".join(lines)
