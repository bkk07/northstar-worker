"""Dry-run mode: print the plan and next actions without executing.

Runs understanding → contract → plan → decide → validate against the
live backend/MCP/LLM and prints each step. Nothing executes: validation
uses the pure checker (no `actions` rows), and the demo task row is
removed afterwards. Backend + MCP server must be up; INCEPTION_API_KEY
must be set (see docs/how-to-run.md).

Usage: python scripts/dry_run.py "Replace ... ORD-1942 (ticket TCK-101)." [--actions 3]
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "common"))
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))


def _load_env() -> None:
    for line in (REPO_ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            name, _, value = line.partition("=")
            os.environ.setdefault(name.strip(), value.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a plan and next actions.")
    parser.add_argument("task", help="Operator task text in quotes")
    parser.add_argument("--actions", type=int, default=3, help="Decisions to preview")
    args = parser.parse_args()

    _load_env()
    from agent.contract.action_validator import validate_action
    from agent.contract.models import Contract
    from agent.runtime import wiring
    from database import session as session_factory
    from database.models.worker.task import Task, TaskContract

    mcp_url = os.environ.get("MCP_URL", "http://127.0.0.1:8002")
    runner = session_factory.runner_engine()
    task_id = uuid.uuid4()
    setup = session_factory.session_for(runner)
    setup.add(
        Task(
            id=task_id,
            text=args.task,
            mode="explicit",
            status="running",
            current_state="running",
            created_by="dry-run",
        )
    )
    setup.commit()
    setup.close()
    try:
        httpx.post(
            f"{mcp_url}/admin/tasks/{task_id}/capabilities",
            json={"capabilities": ["read", "read.fallback", "probe", "browser"]},
            timeout=10,
        ).raise_for_status()

        understanding = wiring.understanding_service()
        interpretation = understanding.interpret(args.task)
        print(f"interpretation: {interpretation.summary}")
        print(
            f"  effects={interpretation.requested_effects} "
            f"codes={interpretation.mentioned_codes} "
            f"unsupported={interpretation.unsupported}"
        )

        contract = wiring.contract_service().build_contract(str(task_id), args.task)
        print(f"contract: {contract.status} caps={contract.capabilities}")
        for effect in contract.effects:
            print(f"  effect={effect.effect} params={effect.params}")
        for item in contract.ambiguity:
            print(f"  ambiguity: {item}")
        if contract.status != "ok":
            return

        steps = wiring.planning_service().create_plan(contract)
        print(f"plan ({len(steps)} steps):")
        for number, step in enumerate(steps, 1):
            print(f"  {number}. [{step['tool']}] {step['step']} — {step['purpose']}")

        decision = wiring.decision_service()
        failures = 0
        error = ""
        shown = 0
        contract_model = Contract.model_validate(contract.model_dump())
        while shown < args.actions:
            action = decision.next_action(contract_model, steps, 0, [], {}, error, failures)
            outcome = validate_action(action.model_dump(), contract_model)
            verdict = "VALID" if outcome.valid else f"INVALID: {'; '.join(outcome.errors)}"
            print(f"action: {action.tool} {action.params} — {verdict}")
            print(f"  rationale: {action.rationale}")
            shown += 1
            if outcome.valid:
                break
            error = "; ".join(outcome.errors)
            failures += 1
    finally:
        cleanup = session_factory.session_for(runner)
        try:
            cleanup.query(TaskContract).filter(TaskContract.task_id == task_id).delete(
                synchronize_session=False
            )
            cleanup.query(Task).filter(Task.id == task_id).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()


if __name__ == "__main__":
    main()
