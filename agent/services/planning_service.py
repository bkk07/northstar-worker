"""Planning service: contract to ordered steps over registered tools.

The LLM proposes the steps; this service enforces the shape (non-empty,
known tools only) and returns plain step dicts into checkpoint state.
No per-task code paths: the same prompt and checks serve every workflow.
"""

from agent.contract.action_validator import TOOL_META
from agent.contract.models import Contract
from agent.llm.client import MercuryClient
from agent.llm.prompts import get_prompt
from agent.llm.schemas import PlanProposal
from northstar_common.errors import NorthstarError


class PlanningError(NorthstarError):
    """The plan proposal was unusable (not a runtime retry)."""

    code = "PLANNING_ERROR"


class PlanningService:
    """Mercury-backed step planning over the locked contract."""

    def __init__(self, llm: MercuryClient) -> None:
        self._llm = llm

    def create_plan(self, contract: Contract) -> list[dict]:
        """Propose, shape-check, and return ordered plan steps."""
        if contract.status != "ok":
            raise PlanningError(f"cannot plan a {contract.status} contract")
        user = _plan_brief(contract)
        try:
            proposal = self._llm.propose(PlanProposal, get_prompt("plan"), user)
        except NorthstarError as exc:
            raise PlanningError(f"plan proposal failed: {exc}") from None
        unknown = [step.tool for step in proposal.steps if step.tool not in TOOL_META]
        if unknown:
            raise PlanningError(f"plan uses unregistered tools: {sorted(set(unknown))}")
        return [step.model_dump() for step in proposal.steps]


def _plan_brief(contract: Contract) -> str:
    """Ground the planner in the contract (goal, effects, tool list)."""
    lines = [
        f"Goal: {contract.goal}",
        "Effects:",
        *(f"- {effect.effect} {effect.params}" for effect in contract.effects),
        f"Capabilities: {', '.join(contract.capabilities)}",
        f"Registered tools: {', '.join(sorted(TOOL_META))}",
    ]
    return "\n".join(lines)
