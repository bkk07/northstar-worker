"""Single-process task runner (Phase 16: no leases yet).

The runner owns task lifecycle around the graph: PENDING → RUNNING,
stream node transitions into checkpoints + audit, then fold the final
state into a terminal task status. Leases, heartbeats, and crash resume
arrive in Phase 20; parked runs (approval/clarification) already end
the graph cleanly and keep their WAITING task state via the node delta.
"""

import json
import traceback
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from agent.graph.builder import build_graph
from agent.graph.checkpointer import PostgresCheckpointStore
from agent.graph.state import WorkerState, initial_state
from agent.ports.clock import ClockPort
from agent.repositories.task_repository import TaskRepository
from agent.runtime import transitions
from agent.runtime.audit_emitter import AuditEmitter
from northstar_common.enums import TaskState

TERMINAL_MAP = {
    "succeeded": TaskState.SUCCEEDED,
    "failed": TaskState.FAILED,
    "blocked": TaskState.BLOCKED,
    "inconclusive": TaskState.INCONCLUSIVE,
}

RUNNER_OWNER = "runner-single-process"

# Hard ceiling on node transitions per run (read-loop backstop; the
# decide correction loop and validation bound fire first).
MAX_RUN_STEPS = 60


class Runner:
    """Run one task's graph to a terminal (or parked) state."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        clock: ClockPort,
        graph=None,
        audit: AuditEmitter | None = None,
        checkpoints: PostgresCheckpointStore | None = None,
    ) -> None:
        self._sessions = session_factory
        self._clock = clock
        self._graph = graph if graph is not None else build_graph()
        self._audit = audit if audit is not None else AuditEmitter(session_factory, clock)
        self._checkpoints = (
            checkpoints if checkpoints is not None else PostgresCheckpointStore(session_factory)
        )

    def run_task(self, task_id: str, on_node=None) -> dict:
        """Execute a task's graph; return the final state (never raises)."""
        session = self._sessions()
        try:
            repo = TaskRepository(session)
            task = repo.get_task(UUID(task_id))
            if task is None:
                return {"status": "failed", "error": f"unknown task: {task_id}"}
            transitions.assert_not_terminal(TaskState(task.status))
            run = repo.create_run(UUID(task_id), RUNNER_OWNER, self._clock.now())
            if TaskState(task.status) == TaskState.PENDING:
                transitions.assert_allowed(TaskState.PENDING, TaskState.RUNNING)
                repo.set_state(task, TaskState.RUNNING.value)
            session.commit()
            task_text, run_id = task.text, str(run.id)
        finally:
            session.close()

        self._audit.run_event(task_id, run_id, "run.start", {"attempt": run.attempt})
        merged: dict = dict(initial_state(task_id, run_id, task_text))
        steps = 0
        capped = False
        try:
            for chunk in self._graph.stream(
                dict(merged),
                config={"recursion_limit": MAX_RUN_STEPS},
                stream_mode="updates",
            ):
                for node, delta in chunk.items():
                    if isinstance(delta, dict):
                        merged.update(delta)
                    steps += 1
                    if on_node is not None:
                        on_node(node, dict(merged))
                    self._checkpoints.save(run_id, node, _jsonable(merged))
                    self._audit.node_transition(task_id, run_id, node)
                    if steps >= MAX_RUN_STEPS:
                        capped = True
                        break
                if capped:
                    break
        except Exception as exc:
            self._finish(task_id, run_id, TaskState.FAILED)
            self._audit.run_event(
                task_id,
                run_id,
                "run.error",
                {"error": str(exc), "traceback": traceback.format_exc(limit=5)},
            )
            return {**merged, "status": "failed", "error": str(exc)}
        if capped:
            merged["status"] = "inconclusive"
            merged["error"] = f"step cap hit ({MAX_RUN_STEPS} node transitions)"
        terminal = _terminal_for(merged)
        if merged.get("status") in (None, "", "pending"):
            merged["status"] = terminal.value
        self._finish(task_id, run_id, terminal)
        self._audit.run_event(task_id, run_id, "run.end", {"status": merged.get("status", "")})
        return merged

    def _finish(self, task_id: str, run_id: str, terminal: TaskState) -> None:
        """Fold the run into the task row (terminal) and close the run."""
        session = self._sessions()
        try:
            repo = TaskRepository(session)
            task = repo.get_task(UUID(task_id))
            if task is not None and TaskState(task.status) == TaskState.RUNNING:
                transitions.assert_allowed(TaskState.RUNNING, terminal)
                repo.set_state(task, terminal.value)
            run = session.get(repo_run_model(), UUID(run_id))
            if run is not None:
                repo.finish_run(run, self._clock.now())
            session.commit()
        finally:
            session.close()


def _terminal_for(merged: dict) -> TaskState:
    """Terminal task state: decided outcome, or the parked wait it ended in."""
    status = merged.get("status", "")
    if status in TERMINAL_MAP:
        return TERMINAL_MAP[status]
    if merged.get("approval_status") == "pending":
        return TaskState.WAITING_FOR_APPROVAL
    if merged.get("clarification_status") == "pending":
        return TaskState.WAITING_FOR_CLARIFICATION
    return TaskState.INCONCLUSIVE


def repo_run_model():
    """TaskRun model (import here: runner stays import-light for tests)."""
    from database.models.worker.task import TaskRun

    return TaskRun


def _jsonable(state: dict) -> dict:
    """Checkpoint-safe copy (state must stay JSON-serializable)."""
    return json.loads(json.dumps(state, default=str))


def initial_worker_state(task_id: str, run_id: str, task_text: str) -> WorkerState:
    """Seed state for a fresh run (re-exported for CLI/tests)."""
    return initial_state(task_id, run_id, task_text)
