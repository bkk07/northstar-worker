"""Commit authority: HMAC policy-token verification (plan §5, §16).

`browser_submit` commits only with a token whose signature binds
(task, action, params hash). The issuer arrives in Phase 15; this guard
already enforces the contract, so commit is impossible without it.
"""

from collections.abc import Mapping

from northstar_common.tokens import canonical_params_hash, verify_policy_token

SUBMIT_ACTION = "browser_submit"


class TokenDenied(Exception):
    """Token missing, malformed, mismatched, or badly signed."""


def verify_submit_token(token: str, secret: str, task_id: str, params: Mapping) -> None:
    """Raise TokenDenied unless the token authorizes this exact submit."""
    if not token:
        raise TokenDenied("token_denied: submit requires a policy token")
    params_hash = canonical_params_hash(params)
    if not verify_policy_token(token, secret, task_id, SUBMIT_ACTION, params_hash):
        raise TokenDenied("token_denied: token does not match (task, action, params)")
