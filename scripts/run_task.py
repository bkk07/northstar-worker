"""Run one operator task end to end (Phase 16 deliverable CLI).

Creates the task through the backend API, grants its MCP capabilities
(base reads now, contract effect scope after compilation), runs the
single-process runner, and prints the terminal summary with journal
counts. Backend + MCP server must be up; INCEPTION_API_KEY must be set
(see docs/how-to-run.md). Set HEADLESS=0 for a visible browser.

Usage: python scripts/run_task.py "Replace ... ORD-1942 (ticket TCK-101)."
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

BASE_CAPABILITIES = ["read", "read.fallback", "probe", "browser"]


def _load_env() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            name, _, value = line.partition("=")
            os.environ.setdefault(name.strip(), value.strip())


def _grant(mcp_url: str, task_id: str, capabilities: list[str]) -> None:
    response = httpx.post(
        f"{mcp_url}/admin/tasks/{task_id}/capabilities",
        json={"capabilities": capabilities},
        timeout=10,
    )
    response.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one operator task to terminal.")
    parser.add_argument("task", help="Operator task text in quotes")
    parser.add_argument("--mode", default="explicit", help="Task mode (default explicit)")
    parser.add_argument("--backend", default="http://127.0.0.1:8000", help="Backend URL")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:8002", help="MCP URL")
    args = parser.parse_args()

    _load_env()
    os.environ.setdefault("MCP_URL", args.mcp_url)
    from agent.runtime import wiring
    from agent.services.finalization_service import FinalizationService

    task = httpx.post(
        f"{args.backend}/api/tasks",
        json={"text": args.task, "mode": args.mode},
        timeout=10,
    )
    task.raise_for_status()
    task_id = task.json()["id"]
    print(f"task: {task_id}")

    _grant(args.mcp_url, task_id, BASE_CAPABILITIES)
    contract = wiring.contract_service().build_contract(task_id, args.task)
    print(f"contract: {contract.status} caps={contract.capabilities}")
    _grant(args.mcp_url, task_id, sorted(set(BASE_CAPABILITIES + contract.capabilities)))

    final = wiring.runner().run_task(task_id, on_node=_progress)
    print(f"run: {final.get('run_id', '')} status={final.get('status', '')}")
    for line in FinalizationService().summary(final):
        print(f"  {line}")
    _print_journal(task_id, final.get("run_id", ""))
    if final.get("error"):
        print(f"  error: {final['error']}")
        sys.exit(1)


def _progress(node: str, state: dict) -> None:
    """Live node trace (the graph is silent otherwise)."""
    action = state.get("last_action", {})
    extra = ""
    if state.get("validation_error"):
        extra = f" invalid={state['validation_error'][:120]}"
    if state.get("failure", {}).get("type"):
        extra = f" failure={state['failure']['type']}"
    print(
        f"[{node}] action={action.get('tool', '')} cursor={state.get('cursor', '')}{extra}",
        flush=True,
    )


def _print_journal(task_id: str, run_id: str) -> None:
    from database import session as session_factory
    from database.models.worker.action import Action, ActionAttempt

    engine = session_factory.runner_engine()
    session = session_factory.session_for(engine)
    try:
        actions = (
            session.query(Action)
            .filter(Action.run_id == uuid.UUID(run_id))
            .order_by(Action.seq)
            .all()
        )
        attempts = (
            session.query(ActionAttempt)
            .join(Action, Action.id == ActionAttempt.action_id)
            .filter(Action.run_id == uuid.UUID(run_id))
            .count()
        )
        print(f"journal: {len(actions)} actions, {attempts} attempts (task {task_id})")
        for action in actions:
            print(f"  [{action.seq}] {action.tool} {action.status} key={action.mutation_key}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
