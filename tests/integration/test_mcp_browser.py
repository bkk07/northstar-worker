"""Phase 11: browser tools through MCP — the agent's commit path end to end."""

import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest

from agent.adapters.mcp_gateway import MCPToolGateway
from northstar_common.tokens import canonical_params_hash, sign_policy_token

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PORT = 8003
FRONTEND_PORT = 5175
MCP_PORT = 8002
TEST_SECRET = "test-secret"


def _wait_for_port(port: int, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"port {port} never opened")


def _wait_for_health(port: int) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=2).status_code == 200:
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("backend never healthy")


def _terminate(proc) -> None:
    """Terminate a process tree (npm orphans grandchildren on Windows)."""
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                proc.wait(timeout=10)
                return
            except subprocess.TimeoutExpired:
                pass
        proc.kill()


@pytest.fixture(scope="module")
def stack():
    """Backend + Vite + seed + MCP server (proves the agent path)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["common", "backend"])
    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            "backend",
            "--port",
            str(BACKEND_PORT),
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    procs = [backend]
    try:
        _wait_for_health(BACKEND_PORT)
        from database.seeds import loader

        loader.seed()
        npm = shutil.which("npm")
        assert npm, "npm is required for browser-tool tests"
        frontend_env = dict(os.environ)
        frontend_env["BACKEND_URL"] = f"http://127.0.0.1:{BACKEND_PORT}"
        vite = subprocess.Popen(
            [
                npm,
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(FRONTEND_PORT),
                "--strictPort",
            ],
            cwd=REPO_ROOT / "frontend",
            env=frontend_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append(vite)
        _wait_for_port(FRONTEND_PORT, timeout_s=120)
        mcp_env = dict(os.environ)
        mcp_env["PYTHONPATH"] = os.pathsep.join(["common"])
        mcp_env["MCP_PORT"] = str(MCP_PORT)
        mcp_env["READ_API_URL"] = f"http://127.0.0.1:{BACKEND_PORT}"
        mcp_env["FRONTEND_URL"] = f"http://localhost:{FRONTEND_PORT}"
        mcp_env["POLICY_TOKEN_SECRET"] = TEST_SECRET
        mcp = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.server"],
            cwd=REPO_ROOT,
            env=mcp_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append(mcp)
        _wait_for_port(MCP_PORT)
        yield f"http://127.0.0.1:{MCP_PORT}"
    finally:
        for proc in reversed(procs):
            _terminate(proc)


def _grant(mcp_url, task_id, capabilities):
    response = httpx.post(
        f"{mcp_url}/admin/tasks/{task_id}/capabilities", json={"capabilities": capabilities}
    )
    assert response.status_code == 200


def _ref(observation, role=None, name=None, form=None):
    for ref, entry in observation["refs"].items():
        if role and entry.get("role") != role:
            continue
        if name and name.lower() not in (entry.get("name") or "").lower():
            continue
        if form and form.lower() not in (entry.get("form") or "").lower():
            continue
        return ref
    raise AssertionError(f"no ref role={role} name={name} form={form}")


def test_browser_login_flow_through_mcp(stack):
    """Open → navigate → observe → fill → click lands on the queue."""
    task_id = f"weblogin-{uuid.uuid4().hex[:8]}"
    _grant(stack, task_id, ["browser"])
    gateway = MCPToolGateway(stack)
    opened = gateway.browser_open(task_id, "ops")
    assert "/ops" in opened["url"]
    login = gateway.browser_navigate(task_id, "/ops/login")
    name_ref = _ref(login, role="textbox", name="agent name")
    go_ref = _ref(login, role="button", name="log in")
    gateway.browser_fill(task_id, name_ref, "mcp-probe")
    queue = gateway.browser_click(task_id, go_ref)
    assert "/ops/tickets" in queue["url"]
    shot = gateway.browser_screenshot(task_id, "mcp-queue")
    assert shot["path"].endswith(".png")


def test_token_gated_note_commit_through_mcp(stack):
    """Signed token + note capability commits a real note via the UI."""
    task_id = f"webnote-{uuid.uuid4().hex[:8]}"
    _grant(stack, task_id, ["read", "probe", "browser", "ticket.note"])
    gateway = MCPToolGateway(stack)
    gateway.browser_open(task_id, "ops")
    gateway.browser_navigate(task_id, "/ops/login")
    login = gateway.browser_observe(task_id)
    gateway.browser_fill(task_id, _ref(login, role="textbox", name="agent name"), "mcp-probe")
    gateway.browser_click(task_id, _ref(login, role="button", name="log in"))

    detail = gateway.browser_navigate(task_id, "/ops/tickets/TCK-140")
    body_ref = _ref(detail, role="textbox", name="Note text")
    add_ref = _ref(detail, role="button", name="Add note")
    gateway.browser_fill(task_id, body_ref, "MCP commit probe.")
    mutation_key = f"mcp-{uuid.uuid4().hex[:12]}"
    params = {
        "effect": "ticket.note",
        "ticket_code": "TCK-140",
        "kind": "internal",
        "body": "MCP commit probe.",
    }
    token = sign_policy_token(TEST_SECRET, task_id, "browser_submit", canonical_params_hash(params))
    result = gateway.browser_submit(task_id, add_ref, mutation_key, token, params)
    assert result["ok"] is True and result["status"] == 201
    probe = gateway.inspect_state(task_id, "mutation", mutation_key)
    assert probe["found"] is True


def test_form_effect_mismatch_blocked_with_valid_token(stack):
    """A note-capable task cannot commit through the replacement form."""
    task_id = f"webform-{uuid.uuid4().hex[:8]}"
    _grant(stack, task_id, ["browser", "ticket.note"])
    gateway = MCPToolGateway(stack)
    gateway.browser_open(task_id, "ops")
    gateway.browser_navigate(task_id, "/ops/login")
    login = gateway.browser_observe(task_id)
    gateway.browser_fill(task_id, _ref(login, role="textbox", name="agent name"), "mcp-probe")
    gateway.browser_click(task_id, _ref(login, role="button", name="log in"))
    detail = gateway.browser_navigate(task_id, "/ops/tickets/TCK-111")
    review_ref = _ref(detail, role="button", name="Review replacement")
    params = {"effect": "ticket.note", "ticket_code": "TCK-111", "body": "x"}
    token = sign_policy_token(TEST_SECRET, task_id, "browser_submit", canonical_params_hash(params))
    with pytest.raises(RuntimeError, match="capability_denied"):
        gateway.browser_submit(task_id, review_ref, f"mcp-{uuid.uuid4().hex[:8]}", token, params)
