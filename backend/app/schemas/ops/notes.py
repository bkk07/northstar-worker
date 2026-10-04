"""Ops DTOs: notes, replies, status changes, UI flags."""

import uuid

from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """Internal note (never customer-visible)."""

    kind: str = Field(default="internal", pattern="^(internal|customer_reply)$")
    body: str = Field(min_length=1)
    author: str = "ops-agent"


class NoteRead(BaseModel):
    """Ticket note row."""

    id: uuid.UUID
    ticket_id: uuid.UUID
    kind: str
    body: str
    author: str
    mutation_key: str | None


class ReplyCreate(BaseModel):
    """Customer-visible reply (stored as a customer_reply note)."""

    body: str = Field(min_length=1)


class StatusUpdate(BaseModel):
    """Ticket status transition."""

    to_status: str = Field(pattern="^(open|in_progress|waiting_on_customer|resolved|closed)$")


class UiFlags(BaseModel):
    """`/ops` behavior switches armed via fault plans (Phase 9 owns faults)."""

    removed_search_field: bool = False
    dom_drift: bool = False
    stale_rerender: bool = False
