"""Server-side singletons: capabilities, read client, browser sessions.

One set per MCP server process, configured from the environment. Tools
never construct these themselves, so tests and the server share one path.
"""

import os

READ_API_URL_ENV = "READ_API_URL"
FRONTEND_URL_ENV = "FRONTEND_URL"
POLICY_SECRET_ENV = "POLICY_TOKEN_SECRET"
# First-party service credential for backend reads/commits. Must match the
# backend's OPERATOR_TOKEN (same default; set a real secret in both for any
# non-local deploy — the backend refuses to boot otherwise).
OPERATOR_TOKEN_ENV = "OPERATOR_TOKEN"
OPERATOR_TOKEN_DEFAULT = "local-operator-token"

_store = None
_reader = None
_manager = None
_served_versions: dict[str, str] = {}


def store():
    """Process-wide capability store."""
    global _store
    if _store is None:
        from mcp_server.capabilities import CapabilitiesStore

        _store = CapabilitiesStore()
    return _store


def reader():
    """Process-wide GET-only read client (service token, no DB credentials)."""
    global _reader
    if _reader is None:
        from mcp_server.clients.read_api_client import ReadApiClient

        _reader = ReadApiClient(
            os.environ.get(READ_API_URL_ENV, "http://127.0.0.1:8000"),
            api_token=service_token(),
        )
    return _reader


def service_token() -> str:
    """Bearer token the backend accepts as first-party service identity."""
    return os.environ.get(OPERATOR_TOKEN_ENV, OPERATOR_TOKEN_DEFAULT)


def browser_manager():
    """Process-wide browser sessions keyed by task id."""
    global _manager
    if _manager is None:
        from browser.manager import SessionManager

        _manager = SessionManager(
            frontend_origin=os.environ.get(FRONTEND_URL_ENV, "http://localhost:5173"),
            storage_dir=os.environ.get("MCP_STORAGE_DIR", "storage/mcp"),
            screenshot_dir=os.environ.get("MCP_SCREENSHOT_DIR", "screenshots/mcp"),
        )
    return _manager


def policy_secret() -> str:
    """HMAC secret shared with the policy-token issuer (Phase 15)."""
    return os.environ.get(POLICY_SECRET_ENV, "local-policy-secret")


def served_version(task_id: str) -> str | None:
    """Last observation version served to a task (staleness baseline)."""
    return _served_versions.get(task_id)


def set_served_version(task_id: str, version: str) -> None:
    """Record the version just served to a task."""
    _served_versions[task_id] = version
