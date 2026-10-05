"""Deterministic mutation identity (plan §18, layer 1).

`key_for` is stable across retries and resumes: sha256 over the task,
the tool, and the binding params. Operational envelope keys (ephemeral
refs, the key/token carriers) are stripped first, so a re-discovered
ref on retry still yields the same key — and the same key sent as the
`Idempotency-Key` header turns a retried commit into a replay.
"""

import hashlib

from northstar_common.tokens import canonical_params_hash

# Ephemeral carriers: stripped before keying (same set the token guard
# and issuer strip; parity-tested there).
OPERATIONAL_KEYS = frozenset({"ref", "mutation_key", "token"})


def key_for(task_id: str, tool: str, params: dict) -> str:
    """Stable idempotency key for one effect attempt (hex, 32 chars)."""
    binding = {k: v for k, v in params.items() if k not in OPERATIONAL_KEYS}
    digest = hashlib.sha256()
    digest.update(str(task_id).encode("utf-8"))
    digest.update(b"\x00")
    digest.update(str(tool).encode("utf-8"))
    digest.update(b"\x00")
    digest.update(canonical_params_hash(binding).encode("utf-8"))
    return digest.hexdigest()[:32]
