"""Deterministic seed loader (Phase 5).

Builds the reproducible world the catalogue and demos run against:
`python -m database.seeds.loader {seed,reset,hash,check}`.

- `seed` loads YAML through the `ns_app` role (proves grants suffice).
- `reset` truncates all `biz`/`worker` tables (admin role).
- `hash` prints the world hash: canonical business facts only, so
  `reset && seed` reproduces it byte-identically (ids are UUID5 from
  codes, timestamps are excluded by design, dates are days-ago relative).
- `check` runs the seed-consistency checker (see check.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.engine import Connection

from agent.runtime.transitions import ALLOWED_TRANSITIONS as CODE_TRANSITIONS
from database.session import admin_engine, app_engine

SEED_DIR = Path(__file__).parent

BIZ_TABLES = [
    "audit_logs",
    "tool_calls",
    "approvals",
    "agent_runs",
    "customer_ticket_messages",
    "customer_tickets",
    "shop_actions",
    "shop_payments",
    "shop_order_items",
    "shop_orders",
    "cart_items",
    "carts",
    "product_policies",
    "products",
    "app_users",
    "ticket_notes",
    "refunds",
    "replacements",
    "mutation_log",
    "ops_sessions",
    "fault_plans",
    "policies",
    "tickets",
    "order_items",
    "orders",
    "customers",
]

WORKER_TABLES = [
    "audit_events",
    "evidence",
    "verification_results",
    "snapshots",
    "memory_items",
    "clarifications",
    "approvals",
    "action_attempts",
    "actions",
    "policy_decisions",
    "task_contracts",
    "task_checkpoints",
    "task_runs",
    "tasks",
    "allowed_transitions",
]


def _uid(code: str) -> uuid.UUID:
    """Deterministic id from a human code (stable across reset+seed)."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"northstar:{code}")


def _days_ago(days: int | None) -> datetime | None:
    if days is None:
        return None
    return datetime.now(UTC) - timedelta(days=days)


def _load(name: str):
    return yaml.safe_load((SEED_DIR / name).read_text(encoding="utf-8"))


def reset() -> None:
    """Truncate every biz/worker table (admin role owns the tables)."""
    tables = ", ".join([f"biz.{t}" for t in BIZ_TABLES] + [f"worker.{t}" for t in WORKER_TABLES])
    with admin_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


def seed() -> dict[str, int]:
    """Load all YAML seeds idempotently; return per-table row counts."""
    customers = {c["code"]: c for c in _load("customers.yaml")}
    shop_products = _load("products.yaml")
    orders = {o["code"]: o for o in _load("orders.yaml")}
    tickets = {t["code"]: t for t in _load("tickets.yaml")}
    policies = _load("policies.yaml")
    history = _load("history.yaml")

    counts: dict[str, int] = {}
    with app_engine().begin() as conn:
        for code, c in customers.items():
            conn.execute(
                text(
                    "INSERT INTO biz.customers (id, code, name, email) "
                    "VALUES (:id, :code, :name, :email) "
                    "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, "
                    "email = EXCLUDED.email"
                ),
                {"id": _uid(code), "code": code, "name": c["name"], "email": c["email"]},
            )
        counts["customers"] = len(customers)

        for p in shop_products:
            pid = _uid(f"product:{p['slug']}")
            conn.execute(
                text(
                    "INSERT INTO biz.products (id, name, slug, description, category, brand, "
                    "price_paise, image_url, stock, is_active) VALUES (:id, :name, :slug, "
                    ":desc, :cat, :brand, :price, '', :stock, true) "
                    "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, "
                    "description = EXCLUDED.description, category = EXCLUDED.category, "
                    "brand = EXCLUDED.brand, price_paise = EXCLUDED.price_paise, "
                    "stock = EXCLUDED.stock, is_active = true"
                ),
                {
                    "id": pid,
                    "name": p["name"],
                    "slug": p["slug"],
                    "desc": p.get("description", ""),
                    "cat": p["category"],
                    "brand": p.get("brand", ""),
                    "price": p["price_paise"],
                    "stock": p.get("stock", 0),
                },
            )
            pol = p.get("policy", {})
            conn.execute(
                text(
                    "INSERT INTO biz.product_policies (id, product_id, return_allowed, "
                    "return_window_days, refund_allowed, replacement_allowed, "
                    "replacement_window_days, cancellation_allowed, warranty_days, "
                    "policy_text) VALUES (:id, :pid, :ret, :retw, :ref, :rep, :repw, "
                    ":can, :war, :text) "
                    "ON CONFLICT (product_id) DO UPDATE SET return_allowed = "
                    "EXCLUDED.return_allowed, return_window_days = "
                    "EXCLUDED.return_window_days, refund_allowed = EXCLUDED.refund_allowed, "
                    "replacement_allowed = EXCLUDED.replacement_allowed, "
                    "replacement_window_days = EXCLUDED.replacement_window_days, "
                    "cancellation_allowed = EXCLUDED.cancellation_allowed, "
                    "warranty_days = EXCLUDED.warranty_days, "
                    "policy_text = EXCLUDED.policy_text"
                ),
                {
                    "id": _uid(f"policy:{p['slug']}"),
                    "pid": pid,
                    "ret": pol.get("return_allowed", True),
                    "retw": pol.get("return_window_days", 7),
                    "ref": pol.get("refund_allowed", True),
                    "rep": pol.get("replacement_allowed", True),
                    "repw": pol.get("replacement_window_days", 7),
                    "can": pol.get("cancellation_allowed", True),
                    "war": pol.get("warranty_days", 0),
                    "text": pol.get("policy_text", ""),
                },
            )
        counts["products"] = len(shop_products)

        item_ids: dict[str, uuid.UUID] = {}
        for code, o in orders.items():
            conn.execute(
                text(
                    "INSERT INTO biz.orders (id, code, customer_id, status, total_paise, "
                    "paid_paise, placed_at, delivered_at) VALUES (:id, :code, "
                    "(SELECT id FROM biz.customers WHERE code = :ccode), :status, "
                    ":total, :paid, :placed, :delivered) "
                    "ON CONFLICT (code) DO UPDATE SET status = EXCLUDED.status, "
                    "total_paise = EXCLUDED.total_paise, paid_paise = EXCLUDED.paid_paise, "
                    "placed_at = EXCLUDED.placed_at, delivered_at = EXCLUDED.delivered_at"
                ),
                {
                    "id": _uid(code),
                    "code": code,
                    "ccode": o["customer"],
                    "status": o["status"],
                    "total": o["total_paise"],
                    "paid": o["paid_paise"],
                    "placed": _days_ago(o["placed_days_ago"]),
                    "delivered": _days_ago(o["delivered_days_ago"]),
                },
            )
            for item in o["items"]:
                item_id = _uid(f"{code}:{item['sku']}")
                item_ids[f"{code}:{item['sku']}"] = item_id
                conn.execute(
                    text(
                        "INSERT INTO biz.order_items (id, order_id, sku, title, qty, "
                        "unit_paise, category) VALUES (:id, :oid, :sku, :title, :qty, "
                        ":unit, :cat) ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, "
                        "qty = EXCLUDED.qty, unit_paise = EXCLUDED.unit_paise, "
                        "category = EXCLUDED.category"
                    ),
                    {
                        "id": item_id,
                        "oid": _uid(code),
                        "sku": item["sku"],
                        "title": item["title"],
                        "qty": item["qty"],
                        "unit": item["unit_paise"],
                        "cat": item["category"],
                    },
                )
        counts["orders"] = len(orders)

        for code, t in tickets.items():
            conn.execute(
                text(
                    "INSERT INTO biz.tickets (id, code, customer_id, order_id, subject, "
                    "body, category, status, version) VALUES (:id, :code, "
                    "(SELECT id FROM biz.customers WHERE code = :ccode), "
                    "(SELECT id FROM biz.orders WHERE code = :ocode), :subject, :body, "
                    ":category, :status, 1) "
                    "ON CONFLICT (code) DO UPDATE SET subject = EXCLUDED.subject, "
                    "body = EXCLUDED.body, category = EXCLUDED.category, "
                    "status = EXCLUDED.status"
                ),
                {
                    "id": _uid(code),
                    "code": code,
                    "ccode": t["customer"],
                    "ocode": t.get("order"),
                    "subject": t["subject"],
                    "body": t["body"],
                    "category": t["category"],
                    "status": t["status"],
                },
            )
        counts["tickets"] = len(tickets)

        for p in policies:
            conn.execute(
                text(
                    "INSERT INTO biz.policies (id, rule_key, params, version) "
                    "VALUES (:id, :key, CAST(:params AS jsonb), :version) "
                    "ON CONFLICT (rule_key) DO UPDATE SET params = EXCLUDED.params, "
                    "version = EXCLUDED.version"
                ),
                {
                    "id": _uid(f"policy:{p['rule_key']}"),
                    "key": p["rule_key"],
                    "params": json.dumps(p["params"]),
                    "version": p["version"],
                },
            )
        counts["policies"] = len(policies)

        for r in history.get("refunds", []):
            refund_id = _uid(f"hist:{r['key']}")
            conn.execute(
                text(
                    "INSERT INTO biz.refunds (id, order_id, customer_id, ticket_id, "
                    "amount_paise, status, mutation_key) VALUES (:id, "
                    "(SELECT id FROM biz.orders WHERE code = :ocode), "
                    "(SELECT id FROM biz.customers WHERE code = :ccode), "
                    "(SELECT id FROM biz.tickets WHERE code = :tcode), "
                    ":amount, :status, :key) ON CONFLICT (mutation_key) DO NOTHING"
                ),
                {
                    "id": refund_id,
                    "ocode": r["order"],
                    "ccode": r["customer"],
                    "tcode": r["ticket"],
                    "amount": r["amount_paise"],
                    "status": r["status"],
                    "key": r["key"],
                },
            )
            conn.execute(
                text(
                    "INSERT INTO biz.mutation_log (id, mutation_key, kind, entity_id) "
                    "VALUES (:id, :key, 'refund', :eid) ON CONFLICT (mutation_key) DO NOTHING"
                ),
                {"id": _uid(f"histlog:{r['key']}"), "key": r["key"], "eid": refund_id},
            )
        for r in history.get("replacements", []):
            replacement_id = _uid(f"hist:{r['key']}")
            conn.execute(
                text(
                    "INSERT INTO biz.replacements (id, order_id, order_item_id, customer_id, "
                    "ticket_id, status, mutation_key) VALUES (:id, "
                    "(SELECT id FROM biz.orders WHERE code = :ocode), :iid, "
                    "(SELECT id FROM biz.customers WHERE code = :ccode), "
                    "(SELECT id FROM biz.tickets WHERE code = :tcode), "
                    ":status, :key) ON CONFLICT (mutation_key) DO NOTHING"
                ),
                {
                    "id": replacement_id,
                    "ocode": r["order"],
                    "iid": item_ids[f"{r['order']}:{r['item_sku']}"],
                    "ccode": r["customer"],
                    "tcode": r["ticket"],
                    "status": r["status"],
                    "key": r["key"],
                },
            )
            conn.execute(
                text(
                    "INSERT INTO biz.mutation_log (id, mutation_key, kind, entity_id) "
                    "VALUES (:id, :key, 'replacement', :eid) "
                    "ON CONFLICT (mutation_key) DO NOTHING"
                ),
                {"id": _uid(f"histlog:{r['key']}"), "key": r["key"], "eid": replacement_id},
            )
        counts["history"] = len(history.get("refunds", [])) + len(history.get("replacements", []))

        # Enforcement config, not world state: `reset` truncates it, so every
        # seed restores the code table (the DB trigger reads this, not Python).
        for frm, tos in CODE_TRANSITIONS.items():
            for to in tos:
                conn.execute(
                    text(
                        "INSERT INTO worker.allowed_transitions (from_status, to_status) "
                        "VALUES (:frm, :to) ON CONFLICT DO NOTHING"
                    ),
                    {"frm": frm.value, "to": to.value},
                )
    return counts


def compute_world_hash(conn: Connection) -> str:
    """Hash of canonical business facts (no ids, no timestamps)."""
    queries = [
        "SELECT code, name, email FROM biz.customers ORDER BY code",
        "SELECT o.code, c.code, o.status, o.total_paise, o.paid_paise "
        "FROM biz.orders o JOIN biz.customers c ON c.id = o.customer_id ORDER BY o.code",
        "SELECT o.code, i.sku, i.title, i.qty, i.unit_paise, i.category "
        "FROM biz.order_items i JOIN biz.orders o ON o.id = i.order_id "
        "ORDER BY o.code, i.sku",
        "SELECT t.code, c.code, COALESCE(o.code, ''), t.subject, t.body, t.category, t.status "
        "FROM biz.tickets t JOIN biz.customers c ON c.id = t.customer_id "
        "LEFT JOIN biz.orders o ON o.id = t.order_id ORDER BY t.code",
        "SELECT r.mutation_key, o.code, c.code, t.code, r.amount_paise, r.status "
        "FROM biz.refunds r JOIN biz.orders o ON o.id = r.order_id "
        "JOIN biz.customers c ON c.id = r.customer_id "
        "JOIN biz.tickets t ON t.id = r.ticket_id ORDER BY r.mutation_key",
        "SELECT r.mutation_key, o.code, i.sku, c.code, t.code, r.status "
        "FROM biz.replacements r JOIN biz.orders o ON o.id = r.order_id "
        "JOIN biz.order_items i ON i.id = r.order_item_id "
        "JOIN biz.customers c ON c.id = r.customer_id "
        "JOIN biz.tickets t ON t.id = r.ticket_id ORDER BY r.mutation_key",
        "SELECT rule_key, params::text, version FROM biz.policies ORDER BY rule_key",
        "SELECT slug, name, category, brand, price_paise, stock FROM biz.products "
        "ORDER BY slug",
        "SELECT p.slug, pp.return_allowed, pp.return_window_days, pp.refund_allowed, "
        "pp.replacement_allowed, pp.replacement_window_days, pp.cancellation_allowed, "
        "pp.warranty_days FROM biz.product_policies pp JOIN biz.products p "
        "ON p.id = pp.product_id ORDER BY p.slug",
    ]
    digest = hashlib.sha256()
    for query in queries:
        for row in conn.execute(text(query)).all():
            digest.update(json.dumps(list(row), sort_keys=True).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def print_hash() -> str:
    """Print and return the current world hash."""
    with admin_engine().connect() as conn:
        world_hash = compute_world_hash(conn)
    print(world_hash)
    return world_hash


def main() -> None:
    """CLI: seed | reset | hash | check."""
    parser = argparse.ArgumentParser(description="Northstar seed loader (Phase 5).")
    parser.add_argument("command", choices=["seed", "reset", "hash", "check"])
    args = parser.parse_args()
    if args.command == "seed":
        counts = seed()
        print(f"seeded: {counts} hash={print_hash()}")
    elif args.command == "reset":
        reset()
        print("reset: biz + worker truncated")
    elif args.command == "hash":
        print_hash()
    elif args.command == "check":
        from database.seeds.check import run_all_checks

        run_all_checks()


if __name__ == "__main__":
    main()
