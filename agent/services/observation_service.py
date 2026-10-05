"""Observation service: normalize tool outcomes into graph routing.

Every execution lands in exactly one bucket: `success` (keep acting),
`effects_done` (a commit landed; verify it), or `failure` (classify it).
The full tool payload rides in `last_observation` for `decide`; the
journal keeps only summaries. Basic memory rows are written per action
with provenance (`browser` observations are untrusted page data until
the verifier cross-checks them in Phase 21).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from database.models.worker.memory import MemoryItem

READ_TOOLS = frozenset(
    {
        "search_customer",
        "get_customer",
        "search_order",
        "get_order",
        "get_ticket",
        "get_policy",
        "api_get",
        "inspect_state",
    }
)


@dataclass(frozen=True)
class ObservationVerdict:
    """Normalized outcome: routing status plus the decide-facing observation."""

    status: str  # "success" | "effects_done" | "failure"
    observation: dict


class ObservationService:
    """Normalize outcomes and persist basic memory (`ns_runner` writes)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sessions = session_factory

    def observe(
        self, task_id: str, run_id: str, action: dict, result: Mapping
    ) -> ObservationVerdict:
        """Bucket one executed action; write its memory rows; return."""
        _ = task_id
        tool = action.get("tool", "")
        ok = bool(result.get("ok", False))
        if not ok:
            observation = {
                "tool": tool,
                "ok": False,
                "error": str(result.get("error", "unknown error"))[:500],
                "error_type": str(result.get("error_type", "")),
                "mutation_key": str(result.get("mutation_key", "")),
                "mutated": False,
            }
            observation["signals"] = _signal_bundle(action, result, observation)
            self._remember(run_id, action, result, observation, outcome="failure")
            return ObservationVerdict(status="failure", observation=observation)
        payload = result.get("payload", {})
        if not isinstance(payload, dict):
            payload = {"result": payload}
        if tool == "browser_submit":
            observation = {
                "tool": tool,
                "ok": True,
                "status": payload.get("status"),
                "effect": payload.get("effect", ""),
                "mutation_key": str(result.get("mutation_key", "")),
                "mutated": bool(result.get("mutated", False)),
                "body": str(payload.get("body", ""))[:500],
            }
            self._remember(run_id, action, result, observation, outcome="effects_done")
            return ObservationVerdict(status="effects_done", observation=observation)
        observation = {
            "tool": tool,
            "ok": True,
            "payload": payload,
            "mutation_key": str(result.get("mutation_key", "")),
            "mutated": False,
        }
        self._remember(run_id, action, result, observation, outcome="success")
        return ObservationVerdict(status="success", observation=observation)

    def _remember(
        self,
        run_id: str,
        action: dict,
        result: Mapping,
        observation: dict,
        outcome: str,
    ) -> None:
        """One memory row per action (provenance: tool; page data untrusted)."""
        tool = action.get("tool", "")
        if tool in READ_TOOLS:
            source_type, trust = "database", "trusted"
        else:
            source_type, trust = "browser", "untrusted"
        session = self._sessions()
        try:
            session.add(
                MemoryItem(
                    run_id=UUID(run_id),
                    key=f"{tool}:{action.get('seq', 0)}:{outcome}",
                    value=_memory_value(tool, observation),
                    source_type=source_type,
                    source_ref=str(result.get("mutation_key", "") or action.get("ref", "")),
                    trust=trust,
                )
            )
            session.commit()
        finally:
            session.close()


def _signal_bundle(action: dict, result: Mapping, observation: dict) -> dict:
    """Classifier inputs for one failure (the classify node reuses them)."""
    from agent.failures import signals as signal_module
    from agent.failures.classifier import classify

    found = signal_module.extract(dict(action), dict(result), dict(observation))
    return {**signal_module.describe(found), "type": classify(found)}


def _memory_value(tool: str, observation: dict) -> dict:
    """Memory-sized value: commit facts whole, page dumps never."""
    if tool == "browser_submit":
        return {
            "effect": observation.get("effect", ""),
            "status": observation.get("status"),
            "mutation_key": observation.get("mutation_key", ""),
        }
    payload = observation.get("payload")
    if isinstance(payload, dict):
        refs = payload.get("refs", {})
        return {
            "url": payload.get("url", ""),
            "title": payload.get("title", ""),
            "ref_count": len(refs) if isinstance(refs, dict) else 0,
        }
    return {"ok": observation.get("ok", False)}
