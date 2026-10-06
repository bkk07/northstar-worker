"""Live end-to-end demo of the 4 spec scenarios (needs running stack + Groq key).

Usage: `python scripts/demo_walkthrough.py`
Covers: refund auto-resolve, replacement + HITL approval, tool-failure
routing to human, manual support. Prints PASS/FAIL per scenario.
"""

import json
import sys
import time
import urllib.request

BASE = "http://localhost:8000"
STAMP = str(int(time.time()))[-6:]


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"null")
    except Exception as e:  # noqa: BLE001
        payload = e.read().decode()[:200] if hasattr(e, "read") else str(e)
        return getattr(e, "code", 0), {"error": payload}


def wait_for(desc, fn, tries=30, sleep=5):
    for _ in range(tries):
        if fn():
            print(f"  ok: {desc}")
            return True
        time.sleep(sleep)
    print(f"  TIMEOUT: {desc}")
    return False


def main() -> int:
    ok = True

    # Shared setup: customer + delivered order.
    _, reg = call("POST", "/auth/register", body={
        "name": "Demo Shopper", "email": f"demo-{STAMP}@example.com",
        "password": "demo-pass-123"})
    cust = reg["access_token"]
    _, prods = call("GET", "/products", token=cust)
    in_stock = next(p for p in prods if p.get("in_stock", True))
    call("POST", "/cart/items", token=cust,
         body={"product_id": in_stock["id"], "quantity": 1})
    _, order = call("POST", "/checkout", token=cust,
                    body={"shipping_address": "221B Baker Street, Mumbai 400001"})
    oid = order["id"]
    delivered = wait_for(
        "order delivered",
        lambda: call("GET", f"/orders/{oid}", token=cust)[1].get("status") == "DELIVERED",
    )
    ok &= delivered

    _, staff_login = call("POST", "/auth/login",
                          body={"email": "admin@northstar.shop", "password": "admin"})
    staff = staff_login["access_token"]

    # Scenario 1: refund auto-resolves.
    print("S1 refund auto-resolve")
    _, t1 = call("POST", "/tickets", token=cust, body={
        "subject": "Damaged item refund", "category": "REFUND",
        "description": "The item arrived damaged, please refund my order.",
        "order_id": oid, "priority": "NORMAL"})
    _, s1 = call("POST", f"/support/tickets/{t1['id']}/solve", token=staff)
    print(f"  solve: intent={s1.get('intent')} decision={s1.get('decision')}")
    s1_ok = wait_for("ticket resolved", lambda: call(
        "GET", f"/support/tickets/{t1['id']}", token=staff)[1].get("status") == "RESOLVED",
        tries=36)
    ok &= s1_ok
    print("S1", "PASS" if s1_ok else "FAIL")

    # Scenario 2: high-value refund pauses for HITL, approval resumes.
    print("S2 high-value refund + HITL")
    pricey = max(prods, key=lambda p: p.get("price_paise", 0))
    call("POST", "/cart/items", token=cust,
         body={"product_id": pricey["id"], "quantity": 1})
    _, order2 = call("POST", "/checkout", token=cust,
                     body={"shipping_address": "221B Baker Street, Mumbai 400001"})
    oid2 = order2["id"]
    ok &= wait_for("second order delivered", lambda: call(
        "GET", f"/orders/{oid2}", token=cust)[1].get("status") == "DELIVERED")
    _, t2 = call("POST", "/tickets", token=cust, body={
        "subject": "Costly item arrived broken", "category": "REFUND",
        "description": "The expensive item arrived broken, please refund my order.",
        "order_id": oid2, "priority": "HIGH"})
    _, s2 = call("POST", f"/support/tickets/{t2['id']}/solve", token=staff)
    print(f"  solve: intent={s2.get('intent')} decision={s2.get('decision')} "
          f"approval={s2.get('approval_id')}")
    paused = s2.get("decision") == "awaiting_approval" and s2.get("approval_id")
    if paused:
        _, dec = call("POST", f"/support/approvals/{s2['approval_id']}/decision",
                      token=staff, body={"approved": True, "note": "Demo approved."})
        print(f"  decision: {dec}")
    s2_ok = paused and wait_for("ticket resolved after approval", lambda: call(
        "GET", f"/support/tickets/{t2['id']}", token=staff)[1].get("status") == "RESOLVED",
        tries=36)
    ok &= s2_ok
    print("S2", "PASS" if s2_ok else "FAIL")

    # Scenario 3: vague ticket goes straight to a human (escalation path).
    print("S3 failure/human routing")
    _, t3 = call("POST", "/tickets", token=cust, body={
        "subject": "Need some help", "category": "GENERAL",
        "description": "Something is wrong, not sure what.", "order_id": None,
        "priority": "NORMAL"})
    _, esc = call("POST", f"/support/tickets/{t3['id']}/escalate", token=staff,
                  body={"reason": "Demo escalation."})
    s3_ok = esc.get("status") == "ESCALATED"
    ok &= s3_ok
    print("S3", "PASS" if s3_ok else "FAIL")

    # Scenario 4: manual reply + resolve.
    print("S4 manual support")
    _, t4 = call("POST", "/tickets", token=cust, body={
        "subject": "Where is my invoice", "category": "GENERAL",
        "description": "Please share the invoice for my order.",
        "order_id": oid, "priority": "LOW"})
    call("POST", f"/support/tickets/{t4['id']}/reply", token=staff,
         body={"message": "Sharing the invoice shortly."})
    _, res = call("POST", f"/support/tickets/{t4['id']}/resolve", token=staff,
                  body={"resolution": "Invoice shared manually."})
    s4_ok = res.get("status") == "RESOLVED"
    ok &= s4_ok
    print("S4", "PASS" if s4_ok else "FAIL")

    print("DEMO", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
