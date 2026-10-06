"""Typed tool I/O schemas (Pydantic v2).

Every MCP tool validates its inputs through these models: malformed calls
fail at the boundary with a schema error, never inside tool logic.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

EffectName = Literal[
    "replacement.create",
    "refund.create",
    "ticket.note",
    "ticket.status",
    "ticket.reply",
]

ProbeKind = Literal["mutation", "replacement", "refund"]


class TaskScoped(BaseModel):
    """Every tool call carries its task for capability scoping."""

    task_id: str = Field(min_length=1)


class SearchCustomerInput(TaskScoped):
    """Find customers by name, email, or code fragment."""

    q: str = Field(min_length=1, max_length=200)


class GetCustomerInput(TaskScoped):
    """One customer by UUID."""

    customer_id: str = Field(min_length=1)


class SearchOrderInput(TaskScoped):
    """Orders of one customer, optionally filtered by code fragment."""

    customer_id: str = Field(min_length=1)
    q: str = Field(default="", max_length=64)


class GetOrderInput(TaskScoped):
    """One order by UUID (items attached)."""

    order_id: str = Field(min_length=1)


class GetTicketInput(TaskScoped):
    """One ticket by UUID."""

    ticket_id: str = Field(min_length=1)


class GetPolicyInput(TaskScoped):
    """One policy rule by key (e.g. P-REF-001)."""

    rule_key: str = Field(min_length=1, max_length=32)


class ApiGetInput(TaskScoped):
    """Fallback GET against an allowlisted path (reads only)."""

    path: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class InspectStateInput(TaskScoped):
    """Probe committed state: by mutation key, or by business identity."""

    kind: ProbeKind
    key: str = Field(min_length=1)
    extra: dict[str, Any] = Field(default_factory=dict)


class BrowserOpenInput(TaskScoped):
    """Open (or reuse) the task's browser session on a commerce surface."""

    target: str = Field(default="ops", pattern="^(ops|shop)$")
    headless: bool = True


class BrowserNavigateInput(TaskScoped):
    """Top-level navigation inside the URL guard."""

    route: str = Field(min_length=1)


class BrowserObserveInput(TaskScoped):
    """Fresh accessibility observation (rebinds refs)."""


class BrowserClickInput(TaskScoped):
    """Click a ref (page state only — never a commit)."""

    ref: str = Field(min_length=1, pattern="^e[0-9]+$")


class BrowserFillInput(TaskScoped):
    """Fill a ref (form state only — never a commit)."""

    ref: str = Field(min_length=1, pattern="^e[0-9]+$")
    value: str = Field(max_length=5000)


class BrowserSubmitInput(TaskScoped):
    """Commit the effect form behind a ref (the ONLY write path)."""

    ref: str = Field(min_length=1, pattern="^e[0-9]+$")
    mutation_key: str = Field(min_length=1, max_length=64)
    token: str = Field(min_length=1)
    params: dict[str, Any] = Field(description="Effect params incl. 'effect'")


class DirectCommitInput(TaskScoped):
    """Commit an effect via the service layer (same token, no browser)."""

    mutation_key: str = Field(min_length=1, max_length=64)
    token: str = Field(min_length=1)
    params: dict[str, Any] = Field(description="Effect params incl. 'effect'")


class BrowserBackInput(TaskScoped):
    """Browser back navigation."""


class BrowserScreenshotInput(TaskScoped):
    """Labeled screenshot into the run's evidence trail."""

    label: str = Field(min_length=1, max_length=80)
