"""Phase 11: MCP reads + probes against the live backend (no frontend)."""

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

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PORT = 8001
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


@pytest.fixture(scope="module")
def stack():
    """Backend + seed + MCP server (reads need no browser)."""
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
        mcp_env = dict(os.environ)
        mcp_env["PYTHONPATH"] = os.pathsep.join(["common"])
        mcp_env["MCP_PORT"] = str(MCP_PORT)
        mcp_env["READ_API_URL"] = f"http://127.0.0.1:{BACKEND_PORT}"
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
        yield f"http://127.0.0.1:{MCP_PORT}", f"http://127.0.0.1:{BACKEND_PORT}"
    finally:
        for proc in reversed(procs):
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture(scope="module")
def gateway(stack):
    """Adapter with a fully granted read/probe task."""
    mcp_url, _ = stack
    task_id = f"reads-{uuid.uuid4().hex[:8]}"
    granted = httpx.post(
        f"{mcp_url}/admin/tasks/{task_id}/capabilities",
        json={"capabilities": ["read", "read.fallback", "probe"]},
    )
    assert granted.status_code == 200
    gateway = MCPToolGateway(mcp_url)
    gateway.task_id = task_id
    return gateway


def _uuid(stack, kind, code):
    _, backend = stack
    if kind == "customer":
        matches = httpx.get(f"{backend}/api/read/customers", params={"q": code}).json()
        return next(c["id"] for c in matches if c["code"] == code)
    return httpx.get(f"{backend}/api/shop/orders/{code}").json()["id"]


def test_search_customer_finds_look_alikes(gateway):
    """Multi-match is data, not an error."""
    result = gateway.search_customer(gateway.task_id, "Priya")
    assert {c["code"] for c in result["customers"]} >= {"C105", "C106"}


def test_get_round_trip(gateway, stack):
    """Customer → orders → order → ticket reads compose."""
    _, backend = stack
    customer_id = _uuid(stack, "customer", "C101")
    assert gateway.get_customer(gateway.task_id, customer_id)["customer"]["code"] == "C101"
    orders = gateway.search_order(gateway.task_id, customer_id)["orders"]
    assert {o["code"] for o in orders} >= {"ORD-1942", "ORD-1955", "ORD-1974"}
    order = gateway.get_order(gateway.task_id, orders[0]["id"])["order"]
    assert order["items"]
    ticket_id = httpx.get(f"{backend}/api/shop/tickets/TCK-101").json()["id"]
    assert gateway.get_ticket(gateway.task_id, ticket_id)["ticket"]["code"] == "TCK-101"


def test_get_policy_and_missing(gateway):
    """Policy thresholds read; unknown rule is not_found."""
    policy = gateway.get_policy(gateway.task_id, "P-REF-001")["policy"]
    assert policy["params"]["max_paise"] == 500000
    with pytest.raises(RuntimeError, match="not_found"):
        gateway.get_policy(gateway.task_id, "P-NOPE")


def test_inspect_by_key_and_identity(gateway, stack):
    """Mutation-key and business-identity probes agree with the DB."""
    _, backend = stack
    by_key = gateway.inspect_state(gateway.task_id, "mutation", "hist-k1")
    assert by_key["found"] is True and by_key["kind"] == "refund"
    assert gateway.inspect_state(gateway.task_id, "mutation", "nope")["found"] is False

    order = httpx.get(f"{backend}/api/shop/orders/ORD-1957").json()
    item_id = next(i["id"] for i in order["items"] if i["sku"] == "BG-12")
    by_identity = gateway.inspect_state(gateway.task_id, "replacement", item_id)
    assert by_identity["found"] is True and by_identity["kind"] == "replacement"

    ticket_id = httpx.get(f"{backend}/api/shop/tickets/TCK-H4").json()["id"]
    order_id = httpx.get(f"{backend}/api/shop/orders/ORD-1973").json()["id"]
    refund = gateway.inspect_state(gateway.task_id, "refund", ticket_id, {"order_id": order_id})
    assert refund["found"] is True and refund["kind"] == "refund"


def test_inspect_unknown_kind_rejected(gateway):
    """Probe kinds outside the registry fail."""
    with pytest.raises(RuntimeError):
        gateway.inspect_state(gateway.task_id, "coupon", "x")


def test_api_get_allowlisted_path(gateway):
    """Allowlisted fallback GET works end to end."""
    result = gateway.api_get(gateway.task_id, "/api/read/policies")
    assert len(result["result"]) == 14
