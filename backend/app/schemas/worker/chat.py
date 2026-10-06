"""Chat DTOs: one operator message in, one assistant reply out."""

import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A single operator chat message."""

    message: str = Field(min_length=1, max_length=2000)


class ChatAction(BaseModel):
    """A follow-up affordance rendered under the reply.

    Links navigate; approval actions render inline Approve/Reject buttons
    that call the approvals API explicitly — typed chat text never decides.
    """

    kind: str
    label: str
    task_id: uuid.UUID | None = None
    href: str | None = None
    approval_id: uuid.UUID | None = None
    decision: str | None = None


class ChatReply(BaseModel):
    """Assistant reply plus optional task binding and follow-up actions."""

    reply: str
    task_id: uuid.UUID | None = None
    actions: list[ChatAction] = Field(default_factory=list)
