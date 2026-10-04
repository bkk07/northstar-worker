"""HMAC policy tokens: commit authority for browser mutations.

On ALLOW, the policy engine signs (task, action, params hash); the MCP
`browser_submit` guard verifies before committing (plan §5, §16).
Pure functions with an explicit secret: the Phase 15 issuer wires settings.

Token wire format: `{task_id}:{action}:{params_hash}:{signature}`
(UUIDs, action names, and hex digests never contain `:`.)
"""

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyToken:
    """Parsed policy token (use `sign_policy_token` / `verify_policy_token`)."""

    task_id: str
    action: str
    params_hash: str
    signature: str

    def encode(self) -> str:
        """Serialize to the wire format."""
        return f"{self.task_id}:{self.action}:{self.params_hash}:{self.signature}"

    @classmethod
    def decode(cls, raw: str) -> "PolicyToken":
        """Parse the wire format; raises ValueError when malformed."""
        parts = raw.split(":")
        if len(parts) != 4 or not all(parts):
            raise ValueError("malformed policy token")
        return cls(task_id=parts[0], action=parts[1], params_hash=parts[2], signature=parts[3])


def _signature(secret: str, task_id: str, action: str, params_hash: str) -> str:
    payload = f"{task_id}:{action}:{params_hash}".encode()
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def sign_policy_token(secret: str, task_id: str, action: str, params_hash: str) -> str:
    """Sign (task, action, params hash) and return the wire-format token."""
    token = PolicyToken(
        task_id=task_id,
        action=action,
        params_hash=params_hash,
        signature=_signature(secret, task_id, action, params_hash),
    )
    return token.encode()


def verify_policy_token(raw: str, secret: str, task_id: str, action: str, params_hash: str) -> bool:
    """True only when the token is well-formed, bound to the expected triple,
    and the signature matches (constant-time comparison). Never raises."""
    try:
        token = PolicyToken.decode(raw)
    except ValueError:
        return False
    if (token.task_id, token.action, token.params_hash) != (task_id, action, params_hash):
        return False
    expected = _signature(secret, task_id, action, params_hash)
    return hmac.compare_digest(token.signature, expected)


def canonical_params_hash(params: Mapping[str, Any]) -> str:
    """Stable hash of action params (issuer and MCP guard must agree).

    Canonical form: JSON with sorted keys and compact separators.
    """
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
