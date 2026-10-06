"""Structured LLM proposals for the support agent (Groq JSON mode)."""

from pydantic import BaseModel, Field

INTENTS = (
    "REFUND",
    "REPLACEMENT",
    "RETURN",
    "CANCELLATION",
    "ORDER_STATUS",
    "DELIVERY",
    "PAYMENT",
    "GENERAL_QUERY",
)


class IntentClassification(BaseModel):
    """Supervisor intent verdict for one ticket."""

    intent: str = Field(
        pattern="^(REFUND|REPLACEMENT|RETURN|CANCELLATION|ORDER_STATUS|DELIVERY|PAYMENT|GENERAL_QUERY)$"
    )
    confidence: float = Field(ge=0.0, le=1.0)
    order_id: str | None = None


class ActionProposal(BaseModel):
    """One proposed mock action (validated before execution)."""

    action_type: str = Field(pattern="^(REFUND|RETURN|REPLACE|CANCEL)$")
    order_id: str
    reason: str = Field(min_length=5, max_length=500)
    amount_paise: int | None = None


class CustomerReply(BaseModel):
    """Drafted customer-facing response."""

    message: str = Field(min_length=5, max_length=2000)
