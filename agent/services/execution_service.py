"""Execution service: journaled MCP tool calls (one action, one attempt).

Journal-first: the action row moves to STARTED (idempotency key
assigned) and the attempt row opens BEFORE the tool runs, so a crash
between journal and tool is recoverable by probe (Phase 19). Tool
failures return as data (`ok=False`) — `observe` classifies them, and
the graph routes to `classify` (Phase 17 fills that taxonomy in).
"""

import os
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from agent.adapters.mcp_gateway import MCPToolGateway
from agent.contract.action_validator import TOOL_META
from agent.failures.classifier import classify_failure
from agent.ports.clock import ClockPort
from agent.runtime import mutation_keys
from agent.runtime.journal import JournalWriter
from northstar_common.errors import NorthstarError
from northstar_common.tokens import canonical_params_hash


class ExecutionError(NorthstarError):
    """The action could not run (unknown tool or journal failure)."""

    code = "EXECUTION_ERROR"


# Tools that commit state: deterministic keys, adopt-before-create, and
# `mutated` journaling. Browser submits go through Chromium; direct tools
# commit the same bound effect through the service layer.
WRITE_TOOLS = frozenset({"browser_submit", "refund_create", "replacement_create"})


@dataclass
class ExecutionResult:
    """One executed action: journal identity plus the tool outcome."""

    action_id: str
    seq: int
    mutation_key: str
    ok: bool
    payload: dict = field(default_factory=dict)
    error: str = ""
    error_type: str = ""
    mutated: bool = False

    def to_result_dict(self) -> dict:
        """State-safe summary (full payload rides along for `observe`)."""
        return {
            "ok": self.ok,
            "payload": self.payload,
            "error": self.error,
            "error_type": self.error_type,
            "mutated": self.mutated,
            "mutation_key": self.mutation_key,
        }


class ExecutionService:
    """Dispatch validated actions to MCP tools with full journaling."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        gateway: MCPToolGateway,
        clock: ClockPort,
    ) -> None:
        self._journal = JournalWriter(session_factory, clock)
        self._gateway = gateway

    def execute(
        self,
        task_id: str,
        run_id: str,
        action: dict,
        policy_decision_id: str | None = None,
    ) -> ExecutionResult:
        """Journal STARTED, call the tool, journal the attempt, return.

        Submits carry deterministic keys (stable across retries) and run
        search-before-create first: an existing entity is adopted without
        a second commit. Same-key retries reuse the failed action's key.
        """
        tool = action.get("tool", "")
        meta = TOOL_META.get(tool)
        if meta is None:
            raise ExecutionError(f"unknown tool: {tool!r}")
        params = dict(action.get("params", {}))
        mutation_key = action.get("reuse_key") or (
            mutation_keys.key_for(task_id, tool, params) if tool in WRITE_TOOLS else None
        )
        started = self._journal.start_action(
            run_id,
            meta.kind,
            tool,
            params,
            canonical_params_hash(params),
            meta.side_effect,
            policy_decision_id,
            mutation_key,
        )
        if tool in WRITE_TOOLS:
            existing = self._search_before_create(task_id, params)
            if existing is not None:
                self._journal.finish_action(started.action_id, "reconciled")
                return ExecutionResult(
                    action_id=str(started.action_id),
                    seq=started.seq,
                    mutation_key=started.mutation_key,
                    ok=True,
                    payload={"ok": True, "reconciled": True, **existing},
                    mutated=False,
                )
        # The adoption above journaled STARTED with zero attempts: nothing
        # ran, so there is nothing to classify — the row tells the story.
        attempt = self._journal.begin_attempt(started.action_id)
        try:
            payload = self._dispatch(task_id, tool, params, started.mutation_key)
        except Exception as exc:
            if self._ensure_open_and_retry(task_id, tool, params, action):
                try:
                    payload = self._dispatch(task_id, tool, params, started.mutation_key)
                except Exception as retry_exc:
                    return self._fail(started, attempt, tool, params, retry_exc)
            else:
                return self._fail(started, attempt, tool, params, exc)
        succeeded = bool(payload.get("ok", True))
        mutated = tool in WRITE_TOOLS and succeeded
        result_view = {
            "ok": succeeded,
            "payload": payload,
            "mutated": mutated,
            "mutation_key": started.mutation_key,
        }
        tool_error_type: str | None = None
        if not succeeded:
            tool_error_type, _ = classify_failure({"tool": tool, "params": params}, result_view, {})
        self._journal.end_attempt(
            attempt.attempt_id,
            "ok" if succeeded else "tool_error",
            _journal_observation(tool, payload, ""),
            tool_error_type,
        )
        self._journal.finish_action(started.action_id, "done" if succeeded else "failed")
        return ExecutionResult(
            action_id=str(started.action_id),
            seq=started.seq,
            mutation_key=started.mutation_key,
            ok=succeeded,
            payload=payload,
            mutated=mutated,
        )

    def _fail(self, started, attempt, tool: str, params: dict, exc: Exception) -> ExecutionResult:
        """Journal a failed attempt and return the classified result."""
        error = str(exc) or type(exc).__name__
        provisional = {"ok": False, "error": error, "error_type": type(exc).__name__}
        failure_type, _ = classify_failure({"tool": tool, "params": params}, provisional, {})
        self._journal.end_attempt(
            attempt.attempt_id,
            "error",
            _journal_observation(tool, {}, error),
            failure_type,
        )
        self._journal.finish_action(started.action_id, "failed")
        return ExecutionResult(
            action_id=str(started.action_id),
            seq=started.seq,
            mutation_key=started.mutation_key,
            ok=False,
            error=error,
            error_type=type(exc).__name__,
        )

    def _ensure_open_and_retry(self, task_id: str, tool: str, params: dict, action: dict) -> bool:
        """Open a missing browser session, then let the caller retry once.

        Reads/clicks/fills before any `browser_open` die on the missing
        session; reopening is read-only navigation, so one blind retry is
        safe. Submits (browser or direct) never take this path.
        """
        if action.get("_ensured_open") or tool in WRITE_TOOLS or tool == "browser_open":
            return False
        action["_ensured_open"] = True
        try:
            self._gateway.browser_open(task_id)
        except Exception:
            pass
        return True

    def _search_before_create(self, task_id: str, params: dict) -> dict | None:
        """Adopt an existing entity for this effect (None when absent).

        Best-effort: unreadable probes return None and the submit goes
        ahead (probe-before-retry still guards the retry).
        """
        from agent.failures import probe as probe_module

        try:
            outcome = probe_module.probe_commit(self._gateway, task_id, "", dict(params))
        except Exception:
            return None
        for hit in (outcome.key_hit, outcome.identity_hit):
            if hit is not None and hit.found:
                return {"entity_id": hit.entity_id, "kind": hit.kind, "via": hit.via}
        return None

    def _dispatch(self, task_id: str, tool: str, params: dict, mutation_key: str) -> dict:
        """One validated action to its gateway call (params are bound)."""
        gateway = self._gateway
        if tool == "search_customer":
            return gateway.search_customer(task_id, params.get("q", ""))
        if tool == "get_customer":
            return gateway.get_customer(task_id, params["customer_id"])
        if tool == "search_order":
            return gateway.search_order(task_id, params["customer_id"], params.get("q", ""))
        if tool == "get_order":
            return gateway.get_order(task_id, params["order_id"])
        if tool == "get_ticket":
            return gateway.get_ticket(task_id, params["ticket_id"])
        if tool == "get_policy":
            return gateway.get_policy(task_id, params["rule_key"])
        if tool == "api_get":
            return gateway.api_get(task_id, params["path"], params.get("params", {}))
        if tool == "inspect_state":
            return gateway.inspect_state(
                task_id, params["kind"], params["key"], params.get("extra", {})
            )
        if tool == "browser_open":
            return gateway.browser_open(
                task_id,
                params.get("target", "ops"),
                params.get("headless", _default_headless()),
            )
        if tool == "browser_navigate":
            return gateway.browser_navigate(task_id, params["route"])
        if tool == "browser_observe":
            return gateway.browser_observe(task_id)
        if tool == "browser_click":
            return gateway.browser_click(task_id, params["ref"])
        if tool == "browser_fill":
            return gateway.browser_fill(task_id, params["ref"], params.get("value", ""))
        if tool == "browser_submit":
            return gateway.browser_submit(
                task_id,
                params["ref"],
                mutation_key,
                params.get("token", ""),
                params,
            )
        if tool == "refund_create":
            return gateway.refund_create(task_id, mutation_key, params.get("token", ""), params)
        if tool == "replacement_create":
            return gateway.replacement_create(
                task_id, mutation_key, params.get("token", ""), params
            )
        if tool == "browser_back":
            return gateway.browser_back(task_id)
        if tool == "browser_screenshot":
            return gateway.browser_screenshot(task_id, params.get("label", "evidence"))
        raise ExecutionError(f"undispatched tool: {tool!r}")


def _default_headless() -> bool:
    """Browser visibility: explicit params win, else HEADLESS env (default on)."""
    return os.environ.get("HEADLESS", "1") != "0"


def _journal_observation(tool: str, payload: dict, error: str) -> dict:
    """Attempt-sized observation: summaries, never page dumps."""
    if error:
        return {"tool": tool, "ok": False, "error": error[:500]}
    if tool in (
        "browser_observe",
        "browser_click",
        "browser_fill",
        "browser_navigate",
        "browser_open",
        "browser_back",
    ):
        refs = payload.get("refs", {})
        return {
            "tool": tool,
            "ok": True,
            "url": payload.get("url", ""),
            "title": payload.get("title", ""),
            "ref_count": len(refs) if isinstance(refs, dict) else 0,
        }
    if tool == "browser_submit":
        return {
            "tool": tool,
            "ok": payload.get("ok", False),
            "status": payload.get("status"),
            "effect": payload.get("effect", ""),
            "mutation_key": payload.get("mutation_key", ""),
        }
    keys = sorted(payload.keys())
    return {"tool": tool, "ok": True, "keys": keys[:20]}
