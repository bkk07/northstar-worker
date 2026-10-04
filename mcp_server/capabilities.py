"""Capability enforcement: per-task tool scopes (plan §14).

Grants are registered out-of-band (runner at contract lock, tests directly):
no MCP tool can grant capabilities, so a task can never widen its own scope.
The registry test asserts the grant path is absent from the tool list.
"""

from mcp_server.registry import SUBMIT_CAPABILITIES


class CapabilityDenied(Exception):
    """Task lacks the capability for a tool call."""


class CapabilitiesStore:
    """In-memory task → capability-set map (per server process)."""

    def __init__(self) -> None:
        self._grants: dict[str, frozenset[str]] = {}

    def grant(self, task_id: str, capabilities: list[str]) -> frozenset[str]:
        """Replace a task's capability set (admin channel only)."""
        granted = frozenset(capabilities)
        self._grants[task_id] = granted
        return granted

    def get(self, task_id: str) -> frozenset[str]:
        """A task's capabilities (empty when never granted)."""
        return self._grants.get(task_id, frozenset())

    def check(self, task_id: str, capability: str) -> None:
        """Raise CapabilityDenied unless the task holds the capability."""
        if capability not in self.get(task_id):
            raise CapabilityDenied(f"capability_denied: task lacks '{capability}'")


def grant_effect(store: CapabilitiesStore, task_id: str, effect: str) -> frozenset[str]:
    """Standard grant for an effect-scoped task: reads, probe, browser, effect."""
    if effect not in SUBMIT_CAPABILITIES:
        raise CapabilityDenied(f"capability_denied: unknown effect '{effect}'")
    return store.grant(task_id, ["read", "read.fallback", "probe", "browser", effect])
