"""Headed replacement demo (Phase 10 definition of done).

A scripted session completes a REAL replacement through the `/ops` UI using
only accessibility refs (role/label/text) — no hard-coded selectors anywhere.
Run on a freshly seeded world (the S11 entities have no replacement yet):

    python -m database.seeds.loader reset
    python -m database.seeds.loader seed
    python scripts/browser_replacement_demo.py  (backend :8000 + vite :5173 up)

Set HEADLESS=1 to run headless where no display exists.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKEND = "http://127.0.0.1:8000"
ORIGIN = "http://localhost:5173"
ORDER_CODE = "ORD-1950"
ITEM_SKU = "CB-05"
TICKET_CODE = "TCK-111"


def api_get(path: str):
    with urllib.request.urlopen(f"{BACKEND}{path}", timeout=10) as response:
        return json.load(response)


def main() -> None:
    from browser.manager import SessionManager

    headless = os.environ.get("HEADLESS", "0") == "1"
    manager = SessionManager(frontend_origin=ORIGIN, storage_dir="storage/demo")
    session = manager.open("demo", headless=headless, slow_mo=150)
    try:
        login = session.navigate("/ops/login")
        name_ref = next(r.ref for r in login.find(role="textbox") if "agent" in r.name.lower())
        go_ref = next(r.ref for r in login.find(role="button", name="log in"))
        session.fill(name_ref, "demo-operator")
        session.click(go_ref)
        session.screenshot("after-login")

        detail = session.navigate(f"/ops/tickets/{TICKET_CODE}")
        form = "Create replacement"
        order_ref = next(r.ref for r in detail.find(role="textbox", name="Order code", form=form))
        sku_ref = next(r.ref for r in detail.find(role="textbox", name="Item SKU", form=form))
        review_ref = next(r.ref for r in detail.find(role="button", name="Review replacement"))
        session.fill(order_ref, ORDER_CODE)
        session.fill(sku_ref, ITEM_SKU)
        session.click(review_ref)

        confirm_obs = session.observe()
        confirm_ref = next(
            r.ref for r in confirm_obs.find(role="button") if "create replacement" in r.name.lower()
        )
        session.network.clear()
        session.click(confirm_ref)
        session.screenshot("after-submit")

        status = session.network.last_status("/api/ops/replacements")
        print(f"mutation status: {status}")
        assert status == 201, f"expected a 201 commit, got {status}"

        order = api_get(f"/api/shop/orders/{ORDER_CODE}")
        item_id = next(i["id"] for i in order["items"] if i["sku"] == ITEM_SKU)
        replacements = api_get(f"/api/read/replacements?order_item_id={item_id}")
        print(f"replacements for {ITEM_SKU}: {len(replacements)}")
        assert len(replacements) == 1, "exactly one replacement must exist"
        print(f"replacement id: {replacements[0]['id']}")
        print("DEMO OK: replacement completed via refs, no hard-coded selectors")
    finally:
        manager.close_all()


if __name__ == "__main__":
    main()
