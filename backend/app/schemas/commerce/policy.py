"""Commerce read DTOs: policy rules."""

from typing import Any

from pydantic import BaseModel


class PolicyRead(BaseModel):
    """Versioned policy rule with its params."""

    rule_key: str
    params: dict[str, Any]
    version: int
