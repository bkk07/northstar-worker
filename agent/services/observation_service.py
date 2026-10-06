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

from agent.memory import injection_detector, provenance
from agent.memory.store import MemoryStore
from agent.repositories.evidence_repository import EvidenceRepository

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
    """Normalize outcomes and persist sourced memory (`ns_runner` writes)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sessions = session_factory
        self._memory = MemoryStore(session_factory)

    def observe(
        self, task_id: str, run_id: str, action: dict, result: Mapping
    ) -> ObservationVerdict:
        """Bucket one executed action; write its memory rows; return."""
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
                "reconciled": bool(payload.get("reconciled", False)),
                "body": str(payload.get("body", ""))[:500],
            }
            self._remember(run_id, action, result, observation, outcome="effects_done")
            self._index_screenshots(task_id, run_id, tool, action, payload)
            return ObservationVerdict(status="effects_done", observation=observation)
        observation = {
            "tool": tool,
            "ok": True,
            "payload": payload,
            "mutation_key": str(result.get("mutation_key", "")),
            "mutated": False,
        }
        self._remember(run_id, action, result, observation, outcome="success")
        self._index_screenshots(task_id, run_id, tool, action, payload)
        return ObservationVerdict(status="success", observation=observation)

    def _index_screenshots(
        self, task_id: str, run_id: str, tool: str, action: dict, payload: dict
    ) -> None:
        """Index screenshot paths as evidence rows (the packet lists them)."""
        shots: list[tuple[str, str]] = []
        if tool == "browser_screenshot" and payload.get("path"):
            label = str(action.get("params", {}).get("label", "evidence"))
            shots.append((label, str(payload["path"])))
        if tool == "browser_submit":
            for key, label in (
                ("before_screenshot", "before-submit"),
                ("after_screenshot", "after-submit"),
            ):
                if payload.get(key):
                    shots.append((label, str(payload[key])))
        if not shots:
            return
        session = self._sessions()
        try:
            repo = EvidenceRepository(session)
            for label, path in shots:
                repo.save_screenshot(UUID(task_id), UUID(run_id), label, path)
            session.commit()
        finally:
            session.close()

    def _remember(
        self,
        run_id: str,
        action: dict,
        result: Mapping,
        observation: dict,
        outcome: str,
    ) -> None:
        """One sourced memory row per action, plus injection flags."""
        tool = action.get("tool", "")
        if tool in READ_TOOLS:
            source_type = "database"
        elif tool == "browser_submit":
            source_type = "browser"
        else:
            source_type = "browser"
        self._memory.record(
            run_id,
            key=f"{tool}:{action.get('seq', 0)}:{outcome}",
            value=_memory_value(tool, observation),
            source_type=source_type,
            source_ref=str(result.get("mutation_key", "") or action.get("ref", "")),
            trust=provenance.classify(source_type),
        )
        flags = injection_detector.detect(_scannable_text(tool, observation))
        if flags:
            self._memory.record(
                run_id,
                key=f"injection:flag:{tool}:{action.get('seq', 0)}",
                value={"flags": flags, "tool": tool},
                source_type=source_type,
                source_ref=str(result.get("mutation_key", "") or action.get("ref", "")),
                trust=provenance.UNTRUSTED,
            )


def _scannable_text(tool: str, observation: dict) -> str:
    """Customer-reachable strings in one observation (page dumps, errors)."""
    if tool == "browser_submit":
        return str(observation.get("body", ""))
    payload = observation.get("payload")
    if isinstance(payload, dict):
        return " ".join(
            str(payload.get(key, "")) for key in ("url", "title", "text", "body", "error")
        )
    return str(observation.get("error", ""))


def _signal_bundle(action: dict, result: Mapping, observation: dict) -> dict:
    """Classifier inputs for one failure (the classify node reuses them)."""
    from agent.failures import signals as signal_module
    from agent.failures.classifier import classify

    found = signal_module.extract(dict(action), dict(result), dict(observation))
    return {**signal_module.describe(found), "type": classify(found)}


def _memory_value(tool: str, observation: dict) -> dict:
    """Memory-sized value: commit facts whole, read facts compact, page dumps never.

    Read payloads used to collapse to a {url, title, ref_count} shell, so a
    run that fetched an order could not recall its item SKUs two steps later
    and re-read forever. Database reads now persist their entity facts in
    compact form (small enough for the prompt block); page dumps still never
    persist whole.
    """
    if tool == "browser_submit":
        return {
            "effect": observation.get("effect", ""),
            "status": observation.get("status"),
            "mutation_key": observation.get("mutation_key", ""),
        }
    payload = observation.get("payload")
    if not isinstance(payload, dict):
        return {"ok": observation.get("ok", False)}
    if tool in READ_TOOLS:
        compacted = _compact_read(tool, payload)
        if compacted is not None:
            return compacted
    refs = payload.get("refs", {})
    return {
        "url": payload.get("url", ""),
        "title": payload.get("title", ""),
        "ref_count": len(refs) if isinstance(refs, dict) else 0,
    }


def _compact_read(tool: str, payload: dict) -> dict | None:
    """Entity facts from one read payload (None when the shape is unknown)."""
    if tool == "get_order":
        order = payload.get("order")
        if not isinstance(order, dict) or not order.get("code"):
            return None
        items = order.get("items")
        compact_items = []
        if isinstance(items, list):
            for item in items[:10]:
                if isinstance(item, dict):
                    compact_items.append(
                        {
                            key: item[key]
                            for key in ("sku", "title", "qty", "unit_paise", "category")
                            if key in item
                        }
                    )
        return {
            "order": order.get("code"),
            "status": order.get("status"),
            "items": compact_items,
        }
    if tool == "get_ticket":
        ticket = payload.get("ticket")
        if not isinstance(ticket, dict) or not ticket.get("code"):
            return None
        return {
            key: ticket[key]
            for key in ("code", "status", "category", "subject")
            if key in ticket
        }
    if tool in ("get_customer", "search_customer"):
        found = payload.get("customer")
        customers = [found] if isinstance(found, dict) else payload.get("customers")
        if not isinstance(customers, list):
            return None
        compacted = [
            {key: customer[key] for key in ("code", "name", "email") if key in customer}
            for customer in customers[:10]
            if isinstance(customer, dict)
        ]
        return {"customers": compacted} if tool == "search_customer" else (
            compacted[0] if compacted else None
        )
    if tool == "search_order":
        orders = payload.get("orders")
        if not isinstance(orders, list):
            return None
        return {
            "orders": [
                {key: order[key] for key in ("code", "status") if key in order}
                for order in orders[:10]
                if isinstance(order, dict)
            ]
        }
    if tool == "get_policy":
        policy = payload.get("policy")
        if not isinstance(policy, dict):
            return None
        summary = {key: policy[key] for key in ("key", "rule_key", "rule", "outcome") if key in policy}
        params = policy.get("params")
        if isinstance(params, dict):
            summary["params"] = str(params)[:200]
        return summary or None
    return None
