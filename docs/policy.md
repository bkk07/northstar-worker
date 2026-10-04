# Policy rule reference (Phase 15)

Eligibility (is the customer entitled?) is separate from authorization
(may the worker act alone?). Both are pure Python over DB facts — the
LLM proposes, never disposes. First failure wins, in this order.

## Eligibility

| Rule | Check |
|---|---|
| E-REPL-001 | Damage reported (category or defect hints), order delivered, within 30 days, no active replacement, item on the order |
| E-REF-001 | Refund amount ≤ amount paid |
| E-REF-002 | Every order-item category refundable (default excludes `final_sale`) |

## Authorization

| Rule | Condition | Outcome |
|---|---|---|
| P-CAP-001 | Action outside the contract's effects/capabilities | BLOCK |
| P-OWN-001 | Contract/order/ticket customers disagree | BLOCK |
| P-REF-001 | Refund ≤ Rs. 5,000 and ≤ 2 refunds in 90 days | ALLOW |
| P-REF-002 | Repeat refunder: ≤ Rs. 1,000 → ALLOW, above → HUMAN_APPROVAL | ALLOW / HUMAN_APPROVAL |
| P-REF-003 | Rs. 5,000 < refund ≤ Rs. 50,000 | HUMAN_APPROVAL |
| P-REF-004 | Refund > Rs. 50,000 or > amount paid | BLOCK |
| P-REPL-001 | Eligible replacement, line total ≤ Rs. 1,50,000 | ALLOW |
| P-REPL-002 | Replacement value above that | HUMAN_APPROVAL |
| P-NOTE-001 | Note/status/reply on the contract's own ticket | ALLOW |
| P-DUP-001 | Active mutation exists (same item, same ticket+order, or same order+amount) | BLOCK (reconcile instead) |
| P-FAIL-CLOSED | Unknown action or missing facts | BLOCK |

Thresholds load from `biz.policies` with code defaults (`agent/policy/rules.py`).

## Tokens

On ALLOW for a submit, the issuer signs (task, `browser_submit`,
payload hash) and the node attaches it to the action; the MCP guard
verifies before committing. Refs and keys are operational envelope on
both sides, so re-discovered refs keep working. Approvals consume
through the same path in Phase 22.

## Trying it

`python scripts/policy_decide.py --contract c.json --action a.json [--facts f.json]`
evaluates one action with no database writes (live facts by default).
