"""Chat controller: operator message in, assistant reply out."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.schemas.worker.chat import ChatReply, ChatRequest
from app.services.worker import chat_runner
from app.services.worker.chat_service import ChatService

router = APIRouter(tags=["worker-chat"])

_staff = require_roles("SUPPORT_AGENT")


@router.post("/api/chat", response_model=ChatReply)
def post_chat(
    payload: ChatRequest,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> ChatReply:
    """Answer one chat message (may launch a background task run). Staff only."""
    return ChatService(session).reply(
        payload.message, start_run=chat_runner.start_run, history=payload.history
    )
