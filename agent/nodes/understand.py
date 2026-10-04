"""understand node (thin): LLM interpretation (Phase 13 wires the service)."""

from agent.graph.state import WorkerState


def understand(state: WorkerState) -> dict:
    """Mark the run live; the stub proposes nothing by itself."""
    return {"status": "running"}
