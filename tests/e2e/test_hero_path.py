"""Phase 16: hero happy path end to end (live stack, marked `llm`).

S1 (damaged-laptop replacement) and S2 (Rs. 2,500 refund) run the real
graph — Mercury 2.5 deciding, Playwright driving `/ops`, policy tokens
gating commits — against backend + MCP + frontend subprocesses. Needs
`RUN_LLM_TESTS=1` with `INCEPTION_API_KEY` (same opt-in as the Mercury
smoke tests); the runner role still cannot write business tables
(`tests/integration/test_grants.py` pins that separately).
"""

import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PORT = 8000
MCP_PORT = 8002
FRONTEND_PORT = 5173
SHARED_SECRET = "e2e-policy-secret"
BASE_CAPABILITIES = ["read", "read.fallback", "probe", "browser"]

S1_TASK = "Replace the damaged ProBook laptop on order ORD-1942 (ticket TCK-101)."
S2_TASK = "Refund Rs. 2,500 for the faulty headphones on order ORD-1943 (ticket TCK-102)."

pytestmark = pytest.mark.llm


def _needs_live():
    if os.environ.get("RUN_LLM_TESTS") != "1" or not os.environ.get("INCEPTION_API_KEY"):
        pytest.skip("hero path needs RUN_LLM_TESTS=1 and INCEPTION_API_KEY")


def _wait_for_port(port: int, timeout_s: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"port {port} never opened")


def _load_env() -> None:
    for line in (REPO_ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            name, _, value = line.partition("=")
            os.environ.setdefault(name.strip(), value.strip())


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def live_stack():
    """Backend + MCP + frontend subprocesses with a shared policy secret."""
    _needs_live()
    _load_env()
    saved = {key: os.environ.get(key) for key in ("MCP_URL", "POLICY_TOKEN_SECRET", "HEADLESS")}
    os.environ["MCP_URL"] = f"http://127.0.0.1:{MCP_PORT}"
    os.environ["POLICY_TOKEN_SECRET"] = SHARED_SECRET
    os.environ["HEADLESS"] = "1"
    pythonpath = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "common")])
    spawned = []

    def _ensure(port, make):
        if _port_open(port):
            return None
        proc = make()
        spawned.append(proc)
        return proc

    def _backend():
        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(BACKEND_PORT),
            ],
            cwd=REPO_ROOT / "backend",
            env={**os.environ, "PYTHONPATH": pythonpath},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _mcp():
        env = dict(os.environ)
        env["PYTHONPATH"] = pythonpath
        env["MCP_PORT"] = str(MCP_PORT)
        env["POLICY_TOKEN_SECRET"] = SHARED_SECRET
        return subprocess.Popen(
            [sys.executable, "-m", "mcp_server.server"],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _frontend():
        return subprocess.Popen(
            [
                "npm.cmd",
                "run",
                "dev",
                "--",
                "--port",
                str(FRONTEND_PORT),
                "--host",
                "127.0.0.1",
                "--strictPort",
            ],
            cwd=REPO_ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    _ensure(BACKEND_PORT, _backend)
    _ensure(MCP_PORT, _mcp)
    _ensure(FRONTEND_PORT, _frontend)
    try:
        _wait_for_port(BACKEND_PORT)
        _wait_for_port(MCP_PORT)
        _wait_for_port(FRONTEND_PORT)
        yield {
            "backend": f"http://127.0.0.1:{BACKEND_PORT}",
            "mcp": f"http://127.0.0.1:{MCP_PORT}",
        }
    finally:
        for proc in spawned:
            proc.terminate()
        for proc in spawned:
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _operator_headers():
    from northstar_common.config import get_settings

    return {"Authorization": f"Bearer {get_settings().operator_token}"}


def _reset_and_seed(backend):
    response = httpx.post(f"{backend}/api/control/reset", headers=_operator_headers(), timeout=30)
    assert response.status_code == 200, response.text
    response = httpx.post(f"{backend}/api/control/seed", headers=_operator_headers(), timeout=60)
    assert response.status_code == 200, response.text


def _run_task(backend, mcp, task_text):
    from agent.runtime import wiring

    task = httpx.post(f"{backend}/api/tasks", json={"text": task_text}, timeout=10)
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]
    httpx.post(
        f"{mcp}/admin/tasks/{task_id}/capabilities",
        json={"capabilities": BASE_CAPABILITIES},
        timeout=10,
    ).raise_for_status()
    contract = wiring.contract_service().build_contract(task_id, task_text)
    assert contract.status == "ok", contract.ambiguity
    httpx.post(
        f"{mcp}/admin/tasks/{task_id}/capabilities",
        json={"capabilities": sorted(set(BASE_CAPABILITIES + contract.capabilities))},
        timeout=10,
    ).raise_for_status()
    final = wiring.runner().run_task(task_id)
    return task_id, final


def _journal_rows(run_id):
    from sqlalchemy import text

    from database import session as session_factory

    session = session_factory.session_for(session_factory.runner_engine())
    try:
        actions = session.execute(
            text("SELECT tool, status FROM worker.actions WHERE run_id = :rid ORDER BY seq"),
            {"rid": uuid.UUID(run_id)},
        ).all()
        attempts = session.execute(
            text(
                "SELECT count(*) FROM worker.action_attempts WHERE action_id IN "
                "(SELECT id FROM worker.actions WHERE run_id = :rid)"
            ),
            {"rid": uuid.UUID(run_id)},
        ).scalar()
        audits = session.execute(
            text("SELECT count(*) FROM worker.audit_events WHERE run_id = :rid"),
            {"rid": uuid.UUID(run_id)},
        ).scalar()
        return actions, attempts, audits
    finally:
        session.close()


def test_s1_replacement_hero_path(live_stack):
    """S1: natural language in, real replacement row out, token-gated."""
    backend, mcp = live_stack["backend"], live_stack["mcp"]
    _reset_and_seed(backend)
    task_id, final = _run_task(backend, mcp, S1_TASK)
    assert final.get("status") == "succeeded", final.get("error", final)

    order = httpx.get(f"{backend}/api/shop/orders/ORD-1942", timeout=10).json()
    item_ids = [item["id"] for item in order["items"]]
    replacements = []
    for item_id in item_ids:
        replacements += httpx.get(
            f"{backend}/api/read/replacements",
            params={"order_item_id": item_id},
            timeout=10,
        ).json()
    assert len(replacements) == 1, replacements
    assert replacements[0]["ticket_id"] is not None

    actions, attempts, audits = _journal_rows(final["run_id"])
    assert actions and all(status == "done" for _, status in actions), actions
    assert attempts >= len(actions) >= 4, (actions, attempts)
    assert audits >= len(actions), audits
    assert any(tool == "browser_submit" for tool, _ in actions), actions
    _ = task_id


def test_s2_refund_hero_path(live_stack):
    """S2: Rs. 2,500 refund commits through the ticket UI with a token."""
    backend, mcp = live_stack["backend"], live_stack["mcp"]
    _reset_and_seed(backend)
    task_id, final = _run_task(backend, mcp, S2_TASK)
    assert final.get("status") == "succeeded", final.get("error", final)

    order = httpx.get(f"{backend}/api/shop/orders/ORD-1943", timeout=10).json()
    refunds = httpx.get(
        f"{backend}/api/read/refunds", params={"order_id": order["id"]}, timeout=10
    ).json()
    assert len(refunds) == 1, refunds
    assert refunds[0]["amount_paise"] == 250000

    actions, attempts, audits = _journal_rows(final["run_id"])
    assert actions and all(status == "done" for _, status in actions), actions
    assert attempts >= len(actions) >= 4, (actions, attempts)
    assert audits >= len(actions), audits
    _ = task_id
