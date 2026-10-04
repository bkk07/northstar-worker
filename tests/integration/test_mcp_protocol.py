"""Phase 11: MCP protocol boundary — no backend or frontend required.

Boots the real SSE server and proves the typed boundary: closed tool
catalogue, schema validation, allowlists, and token/capability gates.
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

from agent.adapters.mcp_gateway import MCPToolGateway
from mcp_server.registry import TOOL_SPECS

REPO_ROOT = Path(__file__).resolve().parents[2]
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


@pytest.fixture(scope="module")
def mcp_url():
    """Live SSE server (no backend dependency for boundary tests)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["common"])
    env["MCP_PORT"] = str(MCP_PORT)
    env["POLICY_TOKEN_SECRET"] = TEST_SECRET
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server.server"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(MCP_PORT)
        yield f"http://127.0.0.1:{MCP_PORT}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="module")
def gateway(mcp_url):
    """Adapter under test (real SSE boundary, per-call connections)."""
    return MCPToolGateway(mcp_url)


def _grant(mcp_url, task_id, capabilities):
    response = httpx.post(
        f"{mcp_url}/admin/tasks/{task_id}/capabilities", json={"capabilities": capabilities}
    )
    assert response.status_code == 200
    return response.json()


def _task(prefix="t") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_tool_catalogue_matches_registry(gateway):
    """Server exposes exactly the registry tools; control plane absent."""
    names = set(gateway.list_tool_names())
    assert names == {spec.name for spec in TOOL_SPECS}
    assert len(names) == 16
    for banned in ("control", "chaos", "reset", "seed", "oracle", "shell", "sql", "grant"):
        assert not any(banned in name for name in names), banned


def test_unknown_tool_rejected(gateway):
    """Calls outside the registry fail (fail closed)."""
    task = _task()
    _grant(gateway._url, task, ["read"])
    with pytest.raises(RuntimeError, match="[Uu]nknown tool"):
        gateway._call("delete_everything", {"task_id": task})


def test_schema_validation_rejects_bad_input(gateway):
    """Malformed calls fail at the boundary (empty query)."""
    task = _task()
    _grant(gateway._url, task, ["read"])
    with pytest.raises(RuntimeError):
        gateway.search_customer(task, "")


def test_api_get_rejects_non_allowlisted_paths(gateway):
    """Control plane, ops writes, and worker API are unreachable via fallback."""
    task = _task()
    _grant(gateway._url, task, ["read.fallback"])
    for path in ("/api/control/seed", "/api/ops/tickets", "/api/worker/x", "/etc/passwd"):
        with pytest.raises(RuntimeError, match="rejected"):
            gateway.api_get(task, path)


def test_capability_gating_before_any_work(gateway):
    """Untenant tasks fail reads; browser needs its own capability."""
    task = _task()
    with pytest.raises(RuntimeError, match="capability_denied"):
        gateway.search_customer(task, "Priya")
    _grant(gateway._url, task, ["read"])
    with pytest.raises(RuntimeError, match="capability_denied"):
        gateway.browser_open(task)


def test_submit_requires_token(gateway):
    """Commit with a missing or bogus token is impossible (no browser touched)."""
    task = _task()
    _grant(gateway._url, task, ["browser", "replacement.create"])
    with pytest.raises(RuntimeError, match="token_denied"):
        gateway.browser_submit(task, "e1", "k", "bogus-token", {"effect": "replacement.create"})


def test_submit_token_bound_to_exact_params(gateway):
    """A token for other params (or tasks) does not authorize."""
    from northstar_common.tokens import canonical_params_hash, sign_policy_token

    task = _task()
    _grant(gateway._url, task, ["browser", "replacement.create"])
    params = {"effect": "replacement.create", "order_code": "ORD-1950"}
    token = sign_policy_token(TEST_SECRET, task, "browser_submit", canonical_params_hash(params))
    with pytest.raises(RuntimeError, match="token_denied"):
        gateway.browser_submit(task, "e1", "k", token, {**params, "order_code": "ORD-1999"})
    _grant(gateway._url, "other-task", ["browser", "replacement.create"])
    with pytest.raises(RuntimeError, match="token_denied"):
        gateway.browser_submit("other-task", "e1", "k", token, params)


def test_effect_scoping_blocks_cross_form_submit(gateway):
    """A replacement-scoped task cannot submit a refund form (no token needed)."""
    task = _task()
    _grant(gateway._url, task, ["browser", "replacement.create"])
    with pytest.raises(RuntimeError, match="capability_denied"):
        gateway.browser_submit(task, "e1", "k", "whatever", {"effect": "refund.create"})
