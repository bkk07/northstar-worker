"""Recovery service: route the failure, apply the strategy, audit it.

The service owns the `recovery.*` audit events and the per-strategy
counters in state; the graph edges do the acting. Retries of a failed
commit never happen here — UNKNOWN_OUTCOME terminates (Phase 19), so
no recovery path can duplicate a side effect.
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from agent.contract.models import Contract
from agent.failures import router
from agent.failures.strategies import apply_strategy
from agent.ports.clock import ClockPort
from agent.runtime.audit_emitter import AuditEmitter


class RecoveryService:
    """Failure-type router with counters and audit (`ns_runner` writes)."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        clock: ClockPort,
        audit: AuditEmitter | None = None,
    ) -> None:
        self._sessions = session_factory
        self._audit = audit
        _ = clock

    def recover(self, task_id: str, run_id: str, state: dict) -> dict:
        """Route, count, apply, and audit one recovery round."""
        failure = state.get("failure", {})
        failure_type = failure.get("type", "")
        counters = dict(state.get("recovery", {}).get("counters", {}))
        strategy, _ = router.route(failure_type, counters)
        delta = self._apply(task_id, run_id, state, strategy, failure_type)
        if delta.pop("recovery_override", None) == router.TERMINATE:
            strategy, delta = router.TERMINATE, {}
        counters[strategy] = counters.get(strategy, 0) + 1
        self._emitter().emit(
            task_id,
            run_id,
            "recover",
            "recovery.decided",
            status=strategy,
            tool=state.get("last_action", {}).get("tool", ""),
            error_type=failure_type,
            retry_count=counters[strategy] - 1,
            payload={"counters": counters},
        )
        return {"recovery": {"strategy": strategy, "counters": counters}, **delta}

    def _apply(
        self, task_id: str, run_id: str, state: dict, strategy: str, failure_type: str
    ) -> dict:
        """Strategy delta over the locked contract (None when absent)."""
        _ = (task_id, run_id)
        contract = state.get("contract")
        parsed = Contract.model_validate(contract) if contract else None
        return apply_strategy(strategy, state, parsed, failure_type)

    def _emitter(self) -> AuditEmitter:
        if self._audit is not None:
            return self._audit
        return AuditEmitter(self._sessions, _system_clock())


def _system_clock():
    """Production clock for the default emitter (tests inject fakes)."""
    from agent.ports.clock import SystemClock

    return SystemClock()
