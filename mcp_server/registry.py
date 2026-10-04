"""Tool registry: the closed, auditable tool catalogue (plan §14).

Single source of truth for name → capability → side effects → idempotency.
The server exposes exactly these tools (a test asserts parity both ways),
and the control plane is absent by construction.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    """One tool's contract: what it may do and what it costs."""

    name: str
    capability: str
    read_only: bool
    side_effect: str
    idempotency: str
    failure_modes: str


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("search_customer", "read", True, "none", "n/a", "empty, multi-match"),
    ToolSpec("get_customer", "read", True, "none", "n/a", "not found"),
    ToolSpec("search_order", "read", True, "none", "n/a", "not found"),
    ToolSpec("get_order", "read", True, "none", "n/a", "not found"),
    ToolSpec("get_ticket", "read", True, "none", "n/a", "not found"),
    ToolSpec("get_policy", "read", True, "none", "n/a", "not found"),
    ToolSpec(
        "api_get",
        "read.fallback",
        True,
        "none",
        "n/a",
        "path not allowlisted → rejected",
    ),
    ToolSpec("inspect_state", "probe", True, "none", "n/a", "unknown kind"),
    ToolSpec(
        "browser_open",
        "browser",
        True,
        "creates session",
        "reuses session",
        "session expired, timeout",
    ),
    ToolSpec(
        "browser_navigate",
        "browser",
        True,
        "navigation",
        "n/a",
        "URL guard rejection",
    ),
    ToolSpec("browser_observe", "browser", True, "none", "n/a", "stale page"),
    ToolSpec(
        "browser_click",
        "browser",
        True,
        "page state only",
        "n/a",
        "stale ref, not found",
    ),
    ToolSpec(
        "browser_fill",
        "browser",
        True,
        "form state only",
        "n/a",
        "not found, validation",
    ),
    ToolSpec(
        "browser_submit",
        "per effect",
        False,
        "commits",
        "key + probe + DB unique",
        "500, timeout, validation, duplicate; valid ALLOW token required",
    ),
    ToolSpec("browser_back", "browser", True, "none", "n/a", "none"),
    ToolSpec("browser_screenshot", "browser", True, "file", "n/a", "none"),
)

TOOL_NAMES = frozenset(spec.name for spec in TOOL_SPECS)

# Effect → the submit capability a task needs for that form.
SUBMIT_CAPABILITIES = frozenset(
    {
        "replacement.create",
        "refund.create",
        "ticket.note",
        "ticket.status",
        "ticket.reply",
    }
)


def spec_for(name: str) -> ToolSpec:
    """Spec for a tool name (KeyError when unknown — fail closed)."""
    for spec in TOOL_SPECS:
        if spec.name == name:
            return spec
    raise KeyError(f"unknown tool: {name}")
