"""Probe-before-retry: find what the failed commit may have left behind.

Order is key-then-identity: the mutation key is exact (same retry, same
key), business identity catches commits whose key never reached the
server. Unreadable probes (transport down, malformed payload) are
bounded — after MAX_PROBE_ROUNDS the run goes INCONCLUSIVE, never
into a blind retry.
"""

from dataclasses import dataclass, field

MAX_PROBE_ROUNDS = 3


@dataclass(frozen=True)
class ProbeHit:
    """One committed-state read: found, what kind, which entity."""

    found: bool
    kind: str = ""
    entity_id: str = ""
    via: str = ""  # "mutation_key" | "business_identity"


@dataclass
class ProbeOutcome:
    """Key probe, identity probe, and whether probing itself worked."""

    key_hit: ProbeHit | None = None
    identity_hit: ProbeHit | None = None
    readable: bool = True
    errors: list = field(default_factory=list)


def probe_commit(gateway, task_id: str, mutation_key: str, identity: dict) -> ProbeOutcome:
    """Probe by key, then by business identity (both best-effort reads)."""
    outcome = ProbeOutcome()
    try:
        payload = gateway.inspect_state(task_id, "mutation", mutation_key)
        outcome.key_hit = _hit(payload, "mutation_key")
    except Exception as exc:
        outcome.readable = False
        outcome.errors.append(f"key probe: {exc}")
    try:
        payload = _probe_identity(gateway, task_id, identity)
        outcome.identity_hit = _hit(payload, "business_identity") if payload else None
    except Exception as exc:
        outcome.readable = False
        outcome.errors.append(f"identity probe: {exc}")
    return outcome


def _probe_identity(gateway, task_id: str, identity: dict) -> dict | None:
    """Identity probe for a submit effect (None when unidentifiable)."""
    effect = identity.get("effect", "")
    if effect == "replacement.create" and identity.get("order_item_id"):
        return gateway.inspect_state(task_id, "replacement", str(identity["order_item_id"]))
    if effect == "refund.create" and identity.get("ticket_id"):
        return gateway.inspect_state(
            task_id,
            "refund",
            str(identity["ticket_id"]),
            {"order_id": str(identity.get("order_id", ""))},
        )
    return None


def _hit(payload: object, via: str) -> ProbeHit:
    """Normalize a ProbeResult-shaped payload (never raises)."""
    if not isinstance(payload, dict):
        return ProbeHit(found=False, via=via)
    return ProbeHit(
        found=bool(payload.get("found", False)),
        kind=str(payload.get("kind", "") or ""),
        entity_id=str(payload.get("entity_id", "") or ""),
        via=via,
    )
