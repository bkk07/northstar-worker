"""Policy-token issuer: commit authority for ALLOWed submits (plan §16).

On ALLOW the policy engine signs (task, `browser_submit`, params hash);
the MCP token guard verifies before committing. The signature covers the
effect payload only — operational keys (`ref`, `mutation_key`, `token`)
are stripped on both sides, so re-discovered refs never invalidate
authority. Approved actions receive tokens only after a consumed approval
(Phase 22); this module signs whatever the service passes it.
"""

from collections.abc import Mapping
from typing import Any

from agent.contract.action_validator import SUBMIT_OPERATIONAL_KEYS
from northstar_common.tokens import canonical_params_hash, sign_policy_token

SUBMIT_ACTION = "browser_submit"


def signable_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Effect payload minus operational keys (the signed surface)."""
    return {k: v for k, v in params.items() if k not in SUBMIT_OPERATIONAL_KEYS}


def issue_submit_token(secret: str, task_id: str, params: Mapping[str, Any]) -> str:
    """Sign (task, browser_submit, payload hash) and return the token."""
    payload_hash = canonical_params_hash(signable_params(params))
    return sign_policy_token(secret, task_id, SUBMIT_ACTION, payload_hash)
