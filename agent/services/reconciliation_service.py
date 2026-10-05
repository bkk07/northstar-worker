"""Reconciliation service: probe-before-retry for unknown outcomes.

Flow per §18: probe by key then identity → match adopts the row
(RECONCILED_EXISTING, journaled, no second submit); mismatch parks
INCONCLUSIVE; absent retries exactly once with the same key; unreadable
probes are bounded (3 rounds) then INCONCLUSIVE. Every round emits
`recovery.probe` audit.
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from agent.adapters.mcp_gateway import MCPToolGateway
from agent.contract.models import Contract
from agent.failures import probe as probe_module
from agent.failures import reconcile as reconcile_module
from agent.failures.probe import MAX_PROBE_ROUNDS, ProbeOutcome
from agent.ports.clock import ClockPort
from agent.runtime.audit_emitter import AuditEmitter
from agent.runtime.journal import JournalWriter


class ReconciliationService:
    """Probe-then-decide for failed commits (`ns_runner` journal + audit)."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        gateway: MCPToolGateway,
        clock: ClockPort,
        audit: AuditEmitter | None = None,
    ) -> None:
        self._sessions = session_factory
        self._gateway = gateway
        self._journal = JournalWriter(session_factory, clock)
        self._audit = audit

    def probe_and_decide(self, task_id: str, run_id: str, state: dict) -> dict:
        """One probe round: adopt, park, or arm a same-key retry."""
        action = dict(state.get("last_action", {}))
        contract = Contract.model_validate(state["contract"])
        mutation_key = action.get("mutation_key", "") or ""
        outcome = probe_module.probe_commit(
            self._gateway, task_id, mutation_key, action.get("params", {})
        )
        rounds = state.get("probe_attempts", 0) + 1
        verdict = self._verdict(outcome, contract, action, rounds)
        self._emitter().emit(
            task_id,
            run_id,
            "probe_reconcile",
            "recovery.probe",
            status=verdict,
            tool=action.get("tool", ""),
            error_type=state.get("failure", {}).get("type", ""),
            retry_count=rounds - 1,
            payload={"mutation_key": mutation_key, "readable": outcome.readable},
        )
        if verdict == reconcile_module.RECONCILED:
            return self._adopt(task_id, action, outcome, rounds)
        if verdict == reconcile_module.MISMATCH:
            detail = list(outcome.errors) or ["entity mismatches contract"]
            return {"probe_status": "mismatch", "probe_attempts": rounds, "probe_detail": detail}
        return {
            "probe_status": "absent",
            "probe_attempts": rounds,
            "last_action": {**action, "reuse_key": mutation_key},
        }

    def _verdict(self, outcome: ProbeOutcome, contract: Contract, action: dict, rounds: int) -> str:
        """Adopt on match; mismatch on foreign rows; retry when absent.

        Unreadable probes get bounded re-probes (same round budget);
        once the budget is spent they park as mismatch (INCONCLUSIVE).
        """
        for hit in (outcome.key_hit, outcome.identity_hit):
            if hit is not None and hit.found:
                verdict, _ = reconcile_module.reconcile_hit(hit, contract, action)
                return verdict
        if not outcome.readable and rounds >= MAX_PROBE_ROUNDS:
            return reconcile_module.MISMATCH
        return "retry"

    def _adopt(self, task_id: str, action: dict, outcome: ProbeOutcome, rounds: int) -> dict:
        """Mark the action reconciled (journal) and route to observe."""
        _ = task_id
        hit = next(h for h in (outcome.key_hit, outcome.identity_hit) if h is not None and h.found)
        try:
            from uuid import UUID

            self._journal.finish_action(UUID(action["action_id"]), "reconciled")
        except Exception:
            pass
        return {
            "probe_status": "exists",
            "probe_attempts": rounds,
            "last_observation": {},
            "observation_status": "success",
            "reconciled_entity": {"kind": hit.kind, "entity_id": hit.entity_id, "via": hit.via},
        }

    def _emitter(self) -> AuditEmitter:
        if self._audit is not None:
            return self._audit
        from agent.ports.clock import SystemClock

        return AuditEmitter(self._sessions, SystemClock())
