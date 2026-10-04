"""understand node (thin): LLM interpretation via the understanding service."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def understand(state: WorkerState) -> dict:
    """Propose a typed reading; the compiler binds it next."""
    interpretation = wiring.understanding_service().interpret(state["task_text"])
    return {"interpretation": interpretation.model_dump(), "status": "running"}
