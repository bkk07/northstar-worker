"""Scenario driver: reset → seed → arm → submit → execute → HITL → score.

Execution runs the real single-process Runner in-process (the
`scripts/run_task.py` pattern); every HITL answer — approvals,
clarifications — goes through the public HTTP endpoints only, never
through services or the database. The isolation test pins that:
no `app.*` / `database.*` imports here, and no approval or
clarification service imports anywhere in `eval/`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
import yaml

from eval.metrics import Actual, ScenarioScore, score_scenario
from eval.oracle_client import OracleClient

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(REPO_ROOT), str(REPO_ROOT / "common"), str(REPO_ROOT / "backend")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

BASE_CAPABILITIES = ["read", "read.fallback", "probe", "browser"]

# Parks the harness resolves itself (approve/answer, then resume).
APPROVABLE = frozenset({"HUMAN_APPROVAL", "AUTO_RESOLVE", "FAIL_AND_RECOVER", "INCONCLUSIVE"})
ANSWERABLE = frozenset({"AUTO_RESOLVE", "FAIL_AND_RECOVER", "HUMAN_APPROVAL"})

TERMINAL_STATES = frozenset({"succeeded", "failed", "blocked", "inconclusive"})

HARNESS_APPROVER = "eval-harness"
HARNESS_ANSWER = "Use your best judgment and proceed."


class Harness:
    """One suite run's driver (fresh world per scenario)."""

    def __init__(
        self,
        backend_url: str = "http://127.0.0.1:8000",
        mcp_url: str = "http://127.0.0.1:8002",
        operator_token: str = "local-operator-token",
        scenario_timeout_s: float = 1500.0,
        poll_s: float = 5.0,
    ) -> None:
        self._backend = backend_url.rstrip("/")
        self._mcp = mcp_url.rstrip("/")
        self._operator = {"Authorization": f"Bearer {operator_token}"}
        self._timeout = scenario_timeout_s
        self._poll = poll_s
        self._http = httpx.Client(timeout=30.0)
        self.oracle = OracleClient(backend_url, operator_token)

    def close(self) -> None:
        """Release HTTP sessions."""
        self._http.close()
        self.oracle.close()

    def drive(self, scenario: dict) -> ScenarioScore:
        """Run one scenario to a scored result (never raises)."""
        scenario_id = scenario["id"]
        try:
            return self._drive(scenario)
        except Exception as exc:
            return score_scenario(
                scenario_id,
                scenario["expected_outcome"],
                scenario.get("expected_effects", []),
                Actual(terminal="error", error=f"{type(exc).__name__}: {exc}"[:300]),
            )

    def _drive(self, scenario: dict) -> ScenarioScore:
        """Reset, execute with HITL, collect, and score."""
        expected = self.oracle.expected(scenario["id"])
        self._reset_seed_arm(scenario)
        task_id = self._submit(scenario)
        self._grant(task_id, BASE_CAPABILITIES)
        contract = self._build_contract(task_id, scenario["task"])
        self._grant(
            task_id, sorted(set(BASE_CAPABILITIES + list(contract.get("capabilities", []))))
        )
        outcome = self._execute_with_hitl(task_id, scenario, expected["expected_outcome"])
        actual = self._collect(task_id, scenario, expected, outcome)
        return score_scenario(
            scenario["id"],
            expected["expected_outcome"],
            expected["expected_effects"],
            actual,
        )

    def _reset_seed_arm(self, scenario: dict) -> None:
        """Fresh deterministic world, plus the scenario's fault plan."""
        self._http.post(
            f"{self._backend}/api/control/reset", headers=self._operator
        ).raise_for_status()
        self._http.post(
            f"{self._backend}/api/control/seed", headers=self._operator
        ).raise_for_status()
        fault_plan = scenario.get("fault_plan")
        if fault_plan:
            self._http.post(
                f"{self._backend}/api/control/chaos",
                headers=self._operator,
                json={
                    "fault_type": fault_plan["type"],
                    "target": fault_plan["target"],
                    "trigger": fault_plan.get("trigger", {}),
                    "params": fault_plan.get("params", {}),
                },
            ).raise_for_status()

    def _submit(self, scenario: dict) -> str:
        """Submit through the real API (the task the operator would type)."""
        response = self._http.post(
            f"{self._backend}/api/tasks",
            json={"text": scenario["task"], "mode": scenario.get("mode", "explicit")},
        )
        response.raise_for_status()
        return response.json()["id"]

    def _grant(self, task_id: str, capabilities: list[str]) -> None:
        """Capability grant through the MCP admin surface."""
        response = self._http.post(
            f"{self._mcp}/admin/tasks/{task_id}/capabilities",
            json={"capabilities": capabilities},
        )
        response.raise_for_status()

    @staticmethod
    def _build_contract(task_id: str, task_text: str) -> dict:
        """Compile the contract for capability scope (read-only shape)."""
        from agent.runtime import wiring

        return wiring.contract_service().build_contract(task_id, task_text).model_dump()

    def _execute_with_hitl(self, task_id: str, scenario: dict, expected_outcome: str) -> dict:
        """Run to terminal, answering parks through public endpoints."""
        from agent.runtime import wiring

        parked: str | None = None
        deadline = time.monotonic() + self._timeout
        for _ in range(12):
            wiring.runner().run_task(task_id)
            task = self._task(task_id)
            status = task["status"]
            if status in TERMINAL_STATES:
                return {"terminal": status, "parked_for": parked}
            if status == "waiting_for_approval":
                parked = parked or "approval"
                if expected_outcome not in APPROVABLE:
                    return {"terminal": "parked", "parked_for": "approval"}
                self._approve_task(task_id)
            elif status in ("waiting_for_clarification", "waiting_on_customer"):
                parked = parked or "clarification"
                if expected_outcome not in ANSWERABLE:
                    return {"terminal": "parked", "parked_for": "clarification"}
                self._answer_task(task_id)
            else:
                return {
                    "terminal": "error",
                    "parked_for": parked,
                    "error": f"unknown status {status}",
                }
            if time.monotonic() > deadline:
                return {"terminal": "timeout", "parked_for": parked}
        return {"terminal": "timeout", "parked_for": parked}

    def _task(self, task_id: str) -> dict:
        """Task row through the public API."""
        response = self._http.get(f"{self._backend}/api/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    def _approve_task(self, task_id: str) -> None:
        """Approve the task's pending approval (public endpoint only)."""
        approvals = self._http.get(f"{self._backend}/api/approvals").json()
        match = [a for a in approvals if a["task_id"] == task_id and a["status"] == "pending"]
        if not match:
            raise RuntimeError(f"no pending approval for task {task_id}")
        response = self._http.post(
            f"{self._backend}/api/approvals/{match[0]['id']}/approve",
            json={"approver": HARNESS_APPROVER},
        )
        response.raise_for_status()

    def _answer_task(self, task_id: str) -> None:
        """Answer the task's pending clarification (public endpoint only)."""
        clarifications = self._http.get(f"{self._backend}/api/clarifications").json()
        match = [c for c in clarifications if c["task_id"] == task_id and c["status"] == "pending"]
        if not match:
            raise RuntimeError(f"no pending clarification for task {task_id}")
        response = self._http.post(
            f"{self._backend}/api/clarifications/{match[0]['id']}/answer",
            json={"answer": HARNESS_ANSWER, "answered_by": HARNESS_APPROVER},
        )
        response.raise_for_status()

    def _collect(self, task_id: str, scenario: dict, expected: dict, outcome: dict) -> Actual:
        """Assemble the Actual record from public endpoints + business reads."""
        task = self._task(task_id)
        events = self._http.get(f"{self._backend}/api/tasks/{task_id}/events/history").json()
        packet = self._packet(task_id)
        verification = self._http.get(f"{self._backend}/api/tasks/{task_id}/verification").json()
        policy_outcome = self._policy_outcome(events, packet)
        committed = self._actual_effects(scenario, expected, packet)
        verdicts = [v["verdict"] for v in verification]
        terminal = outcome["terminal"]
        if terminal == "parked" and task["status"] in TERMINAL_STATES:
            terminal = task["status"]
        budget_hit = any(
            e["kind"] == "budget.exceeded" for e in events
        ) or "BUDGET_EXCEEDED" in str(task.get("current_state", ""))
        return Actual(
            terminal=terminal,
            parked_for=outcome.get("parked_for"),
            recovered=any(e["kind"] == "recovery.decided" for e in events),
            policy_outcome=policy_outcome,
            verification_verdict=verdicts[-1] if verdicts else None,
            committed_effects=committed,
            tool_calls=sum(1 for e in events if e["kind"] == "tool.call"),
            retries=sum(1 for e in events if e["kind"] == "recovery.decided"),
            runtime_s=_runtime_s(events),
            budget_exhausted=budget_hit,
            error=outcome.get("error", ""),
        )

    def _packet(self, task_id: str) -> dict | None:
        """Terminal evidence packet (None while the run never ended)."""
        response = self._http.get(f"{self._backend}/api/tasks/{task_id}/evidence")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _policy_outcome(events: list[dict], packet: dict | None) -> str | None:
        """Last policy outcome: packet decision first, audit trail fallback."""
        if packet:
            outcome = ((packet.get("packet", {}) or {}).get("policy", {}) or {}).get(
                "decision", {}
            ) or {}
            if outcome.get("outcome"):
                return str(outcome["outcome"])
        for event in reversed(events):
            if event["kind"] == "policy.decision" and event.get("policy_result"):
                return str(event["policy_result"])
        return None

    def _actual_effects(self, scenario: dict, expected: dict, packet: dict | None) -> list[dict]:
        """Business-state effects, normalized to catalog codes.

        Money moves come from business reads (exact); status changes
        from the ticket read; notes/replies ride the journal commits
        (count-matched, documented in the report notes).
        """
        committed: list[dict] = []
        ticket_code = scenario["ticket_code"]
        journal_commits = 0
        if packet:
            journal_commits = len(
                (((packet.get("packet", {}) or {}).get("journal", {})) or {}).get("committed", [])
            )
        for effect in expected["expected_effects"]:
            kind = effect["effect"]
            if kind == "refund.create":
                committed.extend(self._refunds(effect))
            elif kind == "replacement.create":
                committed.extend(self._replacements(effect))
            elif kind == "ticket.status":
                ticket = self.oracle.ticket_by_code(ticket_code)
                if ticket["status"] != "open":
                    committed.append({"effect": kind, "ticket_code": ticket_code})
            elif kind in ("ticket.note", "ticket.reply"):
                if journal_commits > 0:
                    committed.append({"effect": kind, "ticket_code": ticket_code})
                    journal_commits -= 1
        if not expected["expected_effects"] and journal_commits > 0:
            committed.append({"effect": "unexpected.commit", "ticket_code": ticket_code})
        return committed

    def _refunds(self, effect: dict) -> list[dict]:
        """Refund rows for the effect's ticket, normalized to codes."""
        ticket = self.oracle.ticket_by_code(effect["ticket_code"])
        rows = self.oracle.refunds_for_ticket(ticket["id"])
        order_codes = {}
        return [
            {
                "effect": "refund.create",
                "order_code": order_codes.setdefault(
                    row["order_id"], self._order_code(row["order_id"])
                ),
                "ticket_code": effect["ticket_code"],
                "amount_paise": row["amount_paise"],
                "mutation_key": row["mutation_key"],
            }
            for row in rows
        ]

    def _replacements(self, effect: dict) -> list[dict]:
        """Replacement rows for the effect's order, normalized to codes."""
        order = self.oracle.order_by_code(effect["order_code"])
        ticket_code = effect["ticket_code"]
        committed = []
        for item in order.get("items", []):
            for row in self.oracle.replacements_for_item(item["id"]):
                committed.append(
                    {
                        "effect": "replacement.create",
                        "order_code": effect["order_code"],
                        "ticket_code": ticket_code,
                        "mutation_key": row["mutation_key"],
                    }
                )
        return committed

    def _order_code(self, order_id: str) -> str:
        """Order code for a row id (falls back to the id; never raises)."""
        try:
            response = self._http.get(f"{self._backend}/api/read/orders/{order_id}")
            response.raise_for_status()
            return response.json().get("code", order_id)
        except Exception:
            return order_id


def _runtime_s(events: list[dict]) -> float:
    """Wall time from run.start to the last event (0 when unmeasurable)."""
    try:
        from datetime import datetime

        stamps = [e["ts"] for e in events if e.get("ts")]
        if len(stamps) < 2:
            return 0.0
        start = datetime.fromisoformat(stamps[0])
        end = datetime.fromisoformat(stamps[-1])
        return max(0.0, (end - start).total_seconds())
    except Exception:
        return 0.0


def load_catalog(path: str | None = None) -> list[dict]:
    """Seeded scenario catalog (the same file the oracle reads)."""
    catalog = path or str(REPO_ROOT / "eval" / "scenarios" / "catalog.yaml")
    return yaml.safe_load(Path(catalog).read_text(encoding="utf-8"))
