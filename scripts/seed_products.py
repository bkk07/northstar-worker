"""Seed the Phase 3 storefront catalog (idempotent).

Usage: `python scripts/seed_products.py`
Upserts `database/seeds/products.yaml` into `biz.products` +
`biz.product_policies` (slug is the stable identity).
"""

import sys
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "backend"), str(ROOT / "common"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import text  # noqa: E402

from database.session import app_engine  # noqa: E402


def _uid(code: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"northstar:{code}")


def main() -> None:
    products = yaml.safe_load((ROOT / "database" / "seeds" / "products.yaml").read_text())
    with app_engine().begin() as conn:
        for p in products:
            pid = _uid(f"product:{p['slug']}")
            conn.execute(
                text(
                    "INSERT INTO biz.products (id, name, slug, description, category, brand, "
                    "price_paise, image_url, stock, is_active) VALUES (:id, :name, :slug, "
                    ":desc, :cat, :brand, :price, :img, :stock, true) "
                    "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, "
                    "description = EXCLUDED.description, category = EXCLUDED.category, "
                    "brand = EXCLUDED.brand, price_paise = EXCLUDED.price_paise, "
                    "image_url = EXCLUDED.image_url, "
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
                    "img": p.get("image_url", ""),
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
    print(f"products ready: {len(products)}")


if __name__ == "__main__":
    main()
