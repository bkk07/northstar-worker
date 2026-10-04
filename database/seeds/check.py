"""Seed-consistency checker (Phase 5).

Static checks (no DB): catalogue shape, id range, reference integrity
across YAML files, required varieties (look-alikes, ownership traps,
injection, every fault type, every outcome).
Seeded checks (live DB): every scenario ticket/order exists, refund-history
facts match the seeded rows.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.engine import Connection

SEED_DIR = Path(__file__).parent
CATALOG_PATH = SEED_DIR.parent.parent / "eval" / "scenarios" / "catalog.yaml"

HELD_OUT_MIN = 901  # S901+ reserved for the sealed held-out set (Phase 28)

OUTCOMES = {
    "AUTO_RESOLVE",
    "HUMAN_APPROVAL",
    "CLARIFY",
    "BLOCK",
    "FAIL_AND_RECOVER",
    "INCONCLUSIVE",
}

EFFECT_TYPES = {
    "replacement.create",
    "refund.create",
    "ticket.note",
    "ticket.status",
    "ticket.reply",
}

FAULT_TYPES = {
    "HTTP_500_BEFORE_COMMIT",
    "HTTP_500_AFTER_COMMIT",
    "TIMEOUT",
    "STALE_ELEMENT",
    "REMOVED_SEARCH_FIELD",
    "DOM_DRIFT",
    "VALIDATION_ERROR",
    "DUPLICATE_EFFECT",
    "SESSION_EXPIRY",
}


def _load_seeds() -> dict:
    return {
        name: yaml.safe_load((SEED_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
        for name in ("customers", "orders", "policies", "tickets", "history")
    }


def _load_catalog() -> list:
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))


def _scenario_number(sid: str) -> int:
    match = re.fullmatch(r"S(\d+)", sid)
    if not match:
        raise ValueError(f"bad scenario id: {sid!r}")
    return int(match.group(1))


def check_static() -> list[str]:
    """Catalogue/YAML consistency without a database; returns error strings."""
    errors: list[str] = []
    seeds = _load_seeds()
    catalog = _load_catalog()

    customer_codes = {c["code"] for c in seeds["customers"]}
    order_codes = {o["code"] for o in seeds["orders"]}
    ticket_codes = {t["code"] for t in seeds["tickets"]}

    seen: set[str] = set()
    for scn in catalog:
        sid = scn.get("id", "?")
        if sid in seen:
            errors.append(f"{sid}: duplicate scenario id")
        seen.add(sid)
        try:
            number = _scenario_number(sid)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if number >= HELD_OUT_MIN:
            errors.append(f"{sid}: id must stay below S{HELD_OUT_MIN} (held-out range)")
        if scn.get("expected_outcome") not in OUTCOMES:
            errors.append(f"{sid}: unknown outcome {scn.get('expected_outcome')!r}")
        for effect in scn.get("expected_effects", []):
            if effect.get("effect") not in EFFECT_TYPES:
                errors.append(f"{sid}: effect outside registry: {effect.get('effect')!r}")
        ticket_code = scn.get("ticket_code")
        if ticket_code not in ticket_codes:
            errors.append(f"{sid}: ticket {ticket_code!r} not in tickets.yaml")

    for t in seeds["tickets"]:
        if t["customer"] not in customer_codes:
            errors.append(f"ticket {t['code']}: unknown customer {t['customer']!r}")
        if t.get("order") is not None and t["order"] not in order_codes:
            errors.append(f"ticket {t['code']}: unknown order {t['order']!r}")
    for o in seeds["orders"]:
        if o["customer"] not in customer_codes:
            errors.append(f"order {o['code']}: unknown customer {o['customer']!r}")

    names = [c["name"] for c in seeds["customers"]]
    if not any("Priya Nair" in n for n in names) or not any("Priya Nayar" in n for n in names):
        errors.append("look-alike pair (Priya Nair / Priya Nayar) missing")
    if not any("OVERRIDE" in t["body"] or "obey" in t["body"] for t in seeds["tickets"]):
        errors.append("injection ticket missing")
    if not any(scn.get("facts", {}).get("ownership_ok") is False for scn in catalog):
        errors.append("ownership-trap scenario missing")

    covered_faults = {s.get("fault_plan", {}).get("type") for s in catalog if s.get("fault_plan")}
    missing_faults = FAULT_TYPES - covered_faults
    if missing_faults:
        errors.append(f"fault types without a scenario: {sorted(missing_faults)}")
    covered_outcomes = {s.get("expected_outcome") for s in catalog}
    missing_outcomes = OUTCOMES - covered_outcomes
    if missing_outcomes:
        errors.append(f"outcomes without a scenario: {sorted(missing_outcomes)}")
    return errors


def check_seeded(conn: Connection) -> list[str]:
    """Post-seed checks against the live DB; returns error strings."""
    errors: list[str] = []
    catalog = _load_catalog()
    for scn in catalog:
        ticket_code = scn["ticket_code"]
        found = conn.execute(
            text(
                "SELECT t.id, c.code, o.code FROM biz.tickets t "
                "JOIN biz.customers c ON c.id = t.customer_id "
                "LEFT JOIN biz.orders o ON o.id = t.order_id WHERE t.code = :code"
            ),
            {"code": ticket_code},
        ).one_or_none()
        if found is None:
            errors.append(f"{scn['id']}: ticket {ticket_code} not seeded")
            continue
        expected_order = next(
            t["order"] for t in _load_seeds()["tickets"] if t["code"] == ticket_code
        )
        if (found[2] or None) != expected_order:
            errors.append(f"{scn['id']}: ticket/order link mismatch in DB")

    refund_counts = {
        row[0]: row[1]
        for row in conn.execute(
            text(
                "SELECT c.code, count(*) FROM biz.refunds r "
                "JOIN biz.customers c ON c.id = r.customer_id "
                "WHERE r.status <> 'cancelled' GROUP BY c.code"
            )
        ).all()
    }
    for scn in catalog:
        expected_count = scn.get("facts", {}).get("refunds_last_90d")
        if expected_count is None:
            continue
        ticket_customer = conn.execute(
            text(
                "SELECT c.code FROM biz.tickets t "
                "JOIN biz.customers c ON c.id = t.customer_id WHERE t.code = :code"
            ),
            {"code": scn["ticket_code"]},
        ).scalar()
        actual = refund_counts.get(ticket_customer, 0)
        if actual != expected_count:
            errors.append(f"{scn['id']}: refunds_last_90d fact {expected_count} != seeded {actual}")
    return errors


def run_all_checks() -> None:
    """CLI entry: static checks plus seeded checks; raises on failure."""
    from database.session import admin_engine

    errors = check_static()
    with admin_engine().connect() as conn:
        errors.extend(check_seeded(conn))
    if errors:
        raise SystemExit("seed-consistency errors:\n" + "\n".join(errors))
    print(f"seed-consistency: {len(_load_catalog())} scenarios OK")
