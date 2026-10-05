"""Task runner: leases, budgets, resume, and the graph (Phase 20).

The runner owns task lifecycle around the graph: claim the lease
(SKIP LOCKED), resume from the last checkpoint when one exists, stream
node transitions into checkpoints + audit with budget enforcement,
then fold the final state into a terminal task status and release the
lease. Parked runs (approval/clarification) end the graph cleanly and
keep their WAITING task state.
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
from agent.repositories.checkpoint_repository import CheckpointRepository
from agent.repositories.evidence_repository import EvidenceRepository
from agent.repositories.journal_repository import JournalRepository
from agent.repositories.task_repository import TaskRepository
from agent.runtime import budgets, lease, transitions
from agent.runtime.audit_emitter import AuditEmitter
from agent.runtime.log import log_event
from agent.runtime.resume import fresh_or_resumed
from agent.services.finalization_service import FinalizationService
from northstar_common.enums import TaskState

TERMINAL_MAP = {
    "succeeded": TaskState.SUCCEEDED,
    "failed": TaskState.FAILED,
    "blocked": TaskState.BLOCKED,
    "inconclusive": TaskState.INCONCLUSIVE,
}

RUNNER_OWNER = "runner-single-process"

# Hard ceiling on node transitions per run (backstop behind the §19
# budgets; one loop iteration costs several node visits).
MAX_RUN_STEPS = 400


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
        """Claim, optionally resume, execute, and release (never raises)."""
        try:
            claimed = self._claim(task_id)
        except lease.LeaseDenied as exc:
            return {"status": "failed", "error": str(exc)}
        if claimed is None:
            return {"status": "failed", "error": f"unknown task: {task_id}"}
        task_text, run_id, attempt = claimed

        self._audit.run_event(task_id, run_id, "run.start", {"attempt": attempt})
        log_event("runner", "run.start", task_id=task_id, run_id=run_id, attempt=attempt)
        merged: dict = self._seed_state(task_id, run_id, task_text)
        wall_start = self._clock.monotonic()
        steps = 0
        capped = False
        budget_hit: str | None = None
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
                    self._track_budget(merged, node, wall_start)
                    if on_node is not None:
                        on_node(node, dict(merged))
                    self._checkpoints.save(run_id, node, _jsonable(merged))
                    self._audit.node_transition(
                        task_id,
                        run_id,
                        node,
                        status=str(merged.get("status", "") or ""),
                        payload={
                            "delta_keys": sorted(delta.keys()) if isinstance(delta, dict) else [],
                        },
                    )
                    if steps % 10 == 0:
                        self._beat(run_id)
                    budget_hit = budgets.exceeded(merged)
                    if budget_hit or steps >= MAX_RUN_STEPS:
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
            log_event("runner", "run.error", task_id=task_id, run_id=run_id, error=str(exc))
            return {**merged, "status": "failed", "error": str(exc)}
        if budget_hit:
            merged["status"] = "failed"
            merged["error"] = f"{budgets.BUDGET_EXCEEDED}:{budget_hit}"
            log_event(
                "runner", "budget.exceeded", task_id=task_id, run_id=run_id, budget=budget_hit
            )
        elif capped:
            merged["status"] = "inconclusive"
            merged["error"] = f"step cap hit ({MAX_RUN_STEPS} node transitions)"
        terminal = _terminal_for(merged)
        if merged.get("status") in (None, "", "pending"):
            merged["status"] = terminal.value
        self._finish(task_id, run_id, terminal)
        self._audit.run_event(task_id, run_id, "run.end", {"status": merged.get("status", "")})
        log_event(
            "runner",
            "run.end",
            task_id=task_id,
            run_id=run_id,
            status=merged.get("status", ""),
            steps=steps,
        )
        if terminal in (
            TaskState.SUCCEEDED,
            TaskState.FAILED,
            TaskState.BLOCKED,
            TaskState.INCONCLUSIVE,
        ):
            merged["evidence_ref"] = self._build_packet(task_id, run_id, merged)
        return merged

    def poll_once(self, limit: int = 10) -> list[dict]:
        """Claim and run every claimable task (the daemon loop calls this)."""
        session = self._sessions()
        try:
            ids = lease.claimable_tasks(session, limit)
            session.commit()
        finally:
            session.close()
        return [self.run_task(str(task_id)) for task_id in ids]

    def _claim(self, task_id: str) -> tuple | None:
        """Lease the next attempt; move PENDING tasks to RUNNING."""
        session = self._sessions()
        try:
            task = TaskRepository(session).get_task(UUID(task_id))
            if task is None:
                return None
            run = lease.claim(session, UUID(task_id), RUNNER_OWNER, self._clock.now())
            if TaskState(task.status) == TaskState.PENDING:
                transitions.assert_allowed(TaskState.PENDING, TaskState.RUNNING)
                TaskRepository(session).set_state(task, TaskState.RUNNING.value)
            session.commit()
            return task.text, str(run.id), run.attempt
        finally:
            session.close()

    def _seed_state(self, task_id: str, run_id: str, task_text: str) -> dict:
        """Resume overlay from the last checkpoint, or a fresh seed."""
        session = self._sessions()
        try:
            runs = (
                session.query(repo_run_model())
                .filter(
                    repo_run_model().task_id == UUID(task_id),
                    repo_run_model().id != UUID(run_id),
                )
                .order_by(repo_run_model().attempt.desc())
                .all()
            )
            for prior in runs:
                row = CheckpointRepository(session).latest(prior.id)
                if row is None:
                    continue
                actions = JournalRepository(session).list_by_run(prior.id)
                tail = actions[-1] if actions else None
                last = (
                    {
                        "tool": tail.tool,
                        "status": tail.status,
                        "mutation_key": tail.mutation_key,
                        "params": dict(tail.params or {}),
                    }
                    if tail is not None
                    else None
                )
                return fresh_or_resumed(task_id, run_id, task_text, dict(row.state), last)
            return dict(initial_state(task_id, run_id, task_text))
        finally:
            session.close()

    def _track_budget(self, merged: dict, node: str, wall_start: float) -> None:
        """Fold this transition into the state's budget counters."""
        entry = merged.setdefault("budgets", {})
        entry.setdefault("limits", _limit_overrides())
        used = entry.setdefault("used", {})
        if node == "decide":
            used["iterations"] = used.get("iterations", 0) + 1
        if node == "execute":
            used["tool_calls"] = used.get("tool_calls", 0) + 1
        if node == "recover":
            used["recovery_attempts"] = used.get("recovery_attempts", 0) + 1
        counters = merged.get("recovery", {}).get("counters", {})
        used["total_retries"] = sum(counters.values()) + merged.get("validation_failures", 0)
        used["retries_per_action"] = merged.get("failure", {}).get("count", 0)
        used["runtime_s"] = self._clock.monotonic() - wall_start

    def _beat(self, run_id: str) -> None:
        """Extend the lease heartbeat (best-effort; loss fails the run)."""
        session = self._sessions()
        try:
            if not lease.heartbeat(session, UUID(run_id), RUNNER_OWNER, self._clock.now()):
                raise lease.LeaseDenied(f"lease lost for run {run_id}")
            session.commit()
        finally:
            session.close()

    def _build_packet(self, task_id: str, run_id: str, merged: dict) -> dict:
        """Assemble, persist, and audit the terminal evidence packet."""
        packet = FinalizationService().build_packet(self._sessions, task_id, run_id, merged)
        session = self._sessions()
        try:
            row = EvidenceRepository(session).save_packet(UUID(task_id), packet, packet["summary"])
            session.commit()
            evidence_id = str(row.id)
        finally:
            session.close()
        self._audit.run_event(
            task_id,
            run_id,
            "run.packet",
            {"evidence_id": evidence_id, "headline": packet["summary"][0]},
        )
        log_event(
            "runner",
            "run.packet",
            task_id=task_id,
            run_id=run_id,
            evidence_id=evidence_id,
            headline=packet["summary"][0],
        )
        return {"id": evidence_id, "summary": packet["summary"]}

    def _finish(self, task_id: str, run_id: str, terminal: TaskState) -> None:
        """Fold the run into the task row (terminal) and release the lease."""
        session = self._sessions()
        try:
            repo = TaskRepository(session)
            task = repo.get_task(UUID(task_id))
            if task is not None and TaskState(task.status) == TaskState.RUNNING:
                transitions.assert_allowed(TaskState.RUNNING, terminal)
                repo.set_state(task, terminal.value)
            lease.release(session, UUID(run_id), RUNNER_OWNER, self._clock.now())
            session.commit()
        finally:
            session.close()


def _limit_overrides() -> dict:
    """Env-tunable limits (defaults stay §19; live runs allow more room)."""
    import os

    overrides: dict = {}
    for name, env in (
        ("iterations", "BUDGET_ITERATIONS"),
        ("tool_calls", "BUDGET_TOOL_CALLS"),
        ("retries_per_action", "BUDGET_RETRIES_PER_ACTION"),
        ("total_retries", "BUDGET_TOTAL_RETRIES"),
        ("recovery_attempts", "BUDGET_RECOVERY_ATTEMPTS"),
        ("runtime_s", "BUDGET_RUNTIME_S"),
    ):
        raw = os.environ.get(env)
        if raw:
            try:
                overrides[name] = float(raw)
            except ValueError:
                pass
    return overrides


def _terminal_for(merged: dict) -> TaskState:
    """Terminal task state: decided outcome, or the parked wait it ended in."""
    status = merged.get("status", "")
    if status in TERMINAL_MAP:
        return TERMINAL_MAP[status]
    if merged.get("approval_status") == "pending":
        return TaskState.WAITING_FOR_APPROVAL
    if merged.get("clarification_status") == "pending":
        if merged.get("waiting_on_customer"):
            return TaskState.WAITING_ON_CUSTOMER
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
