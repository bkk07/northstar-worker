"""Chat run driver: task creation is synchronous, the run is a daemon thread.

Mirrors `scripts/run_task.py` (grant base caps -> compile contract -> grant
effect caps -> run to terminal) so chat-started tasks behave exactly like
CLI-started ones. Runs serialize on a module lock; the reply path never
blocks on the runner.
"""

import logging
import os
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
for extra in (str(REPO_ROOT), str(REPO_ROOT / "backend"), str(REPO_ROOT / "common")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

BASE_CAPABILITIES = ["read", "read.fallback", "probe", "browser"]

_RUN_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def _load_env() -> None:
    """Load repo `.env` like `scripts/run_task.py` (servers rarely inherit it)."""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            name, _, value = line.partition("=")
            os.environ.setdefault(name.strip(), value.strip())


_load_env()


def _mark_cancelled(task_id: str) -> None:
    """Cancel a chat-started task the driver never got going.

    `pending -> cancelled` and `running -> cancelled` are both legal
    transitions; anything else means the runner owns the task now.
    """
    from sqlalchemy.orm import Session

    from app.core.deps import get_engine
    from database.models.worker.task import Task

    session = Session(bind=get_engine())
    try:
        row = session.get(Task, task_id)
        if row is not None and row.status in ("pending", "running"):
            row.status = "cancelled"
            row.current_state = "cancelled"
            session.commit()
    finally:
        session.close()


def _drive(task_id: str, task_text: str) -> None:
    """Grant, compile, and run one task to terminal (background thread)."""
    import httpx

    from agent.runtime import wiring

    mcp_url = os.environ.get("MCP_URL", "http://127.0.0.1:8002")

    def grant(capabilities: list[str]) -> None:
        response = httpx.post(
            f"{mcp_url}/admin/tasks/{task_id}/capabilities",
            json={"capabilities": capabilities},
            timeout=10,
        )
        response.raise_for_status()

    with _RUN_LOCK:
        grant(BASE_CAPABILITIES)
        contract = wiring.contract_service().build_contract(task_id, task_text)
        grant(sorted(set(BASE_CAPABILITIES + contract.capabilities)))
        wiring.runner().run_task(task_id)


def start_run(task_id: str, task_text: str) -> None:
    """Launch the background driver; unexpected errors are logged, never raised."""

    def guarded() -> None:
        try:
            _drive(task_id, task_text)
        except Exception:  # noqa: BLE001 - background thread must not kill the server
            logger.exception("chat run failed for task %s", task_id)
            _mark_cancelled(task_id)

    thread = threading.Thread(target=guarded, name=f"chat-run-{task_id}", daemon=True)
    thread.start()
