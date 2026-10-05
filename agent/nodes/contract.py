"""contract node (thin): compile and lock the task contract."""

from agent.graph.state import WorkerState
from agent.runtime import wiring


def contract(state: WorkerState) -> dict:
    """Resolve entities, compile, persist; the edge reads the status."""
    result = wiring.contract_service().build_contract(state["task_id"], state["task_text"])
    if result.status == "ok" and state.get("run_id"):
        wiring.verifier_adapter().snapshot_before(result.model_dump(), state["run_id"])
    wiring.audit_emitter().emit(
        state["task_id"],
        state.get("run_id", ""),
        "contract",
        "contract.compiled",
        status=result.status,
        payload={"effects": len(result.effects), "ambiguity": list(result.ambiguity)},
    )
    return {"contract": result.model_dump(), "contract_status": result.status}
