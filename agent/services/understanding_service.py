"""Understanding service: operator text to a typed interpretation.

One LLM call per task, validated against `Interpretation` before return.
The interpretation proposes; the contract compiler disposes — nothing
here binds entities, amounts, or authority.
"""

from agent.llm.client import MercuryClient
from agent.llm.prompts import get_prompt
from agent.llm.schemas import Interpretation


class UnderstandingService:
    """Mercury-backed interpretation (proposal only)."""

    def __init__(self, llm: MercuryClient) -> None:
        self._llm = llm

    def interpret(self, task_text: str) -> Interpretation:
        """Propose a typed reading of the operator's task."""
        if not task_text or not task_text.strip():
            raise ValueError("empty task text")
        return self._llm.propose(Interpretation, get_prompt("understand"), task_text.strip())
