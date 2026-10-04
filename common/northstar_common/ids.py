"""Deterministic identity helpers (SHA-256).

Mutation keys are stable across retries and resumes: the same
(task, effect) always maps to the same idempotency key, which is what
makes probe-before-retry safe (plan §18).
"""

import hashlib


def sha256_hex(*parts: str) -> str:
    """Hex digest over `|`-joined parts (unambiguous for separator-free parts
    such as UUIDs and dotted effect names)."""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def mutation_key(task_id: str, effect_id: str) -> str:
    """Idempotency key for one contracted effect of one task."""
    return sha256_hex(task_id, effect_id)
