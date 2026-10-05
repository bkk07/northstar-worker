# Independent Verifier (Phase 21)

Proof of outcome is the central thesis: nothing is reported done until
deterministic code confirms the real database state matches the
contract's `ExpectedEffects`.

## Independence

- The `verifier/` package imports only `common` and `database.models`.
  It never imports `agent`, `backend`, or `mcp_server` (import-linter
  contract `verifier-independence` fails the build otherwise).
- Its inputs are the contract (plain data) and DB rows. It never reads
  LLM text, UI banners, or agent evidence.
- Reads use the `ns_verifier` role (SELECT-only). The agent-side
  `VerifierAdapter` persists `worker.snapshots` / `worker.verification_results`
  through the runner role; the verifier package itself only computes.

## Procedure

1. `snapshot_before` is taken at contract lock, scoped to the contract's
   customer/order/ticket IDs plus related rows. First snapshot wins
   (resume-safe). Scope plus whole-table counts are stored.
2. `snapshot_after` is taken at verify time with the same scope.
3. `diff = after - before`: added/removed rows and field-level changes.
4. Per-effect invariants run against the diff and after-state, plus the
   global invariant on every contract.

## Invariants

- **Replacement:** exactly one new active replacement for the item;
  correct customer/order/ticket linkage; status `pending`.
- **Refund:** exactly one new refund; amount equals the contract (paise);
  correct linkage; total refunds on the order within paid.
- **Ticket:** new note with the expected kind/body and a mutation key;
  customer reply present when required; status equals the target.
- **Global:** no removed rows; added rows match the contracted effects
  exactly; customers/orders/items untouched; ticket edits are status
  moves (+version bumps); whole-table count deltas equal the allowed
  adds, so writes outside the scope still fail.

## Verdicts

`verified` (all invariants pass), `failed` (names violated invariants),
`inconclusive` (missing before-snapshot or no effects — never a guess).
Unknown effects fail closed. The graph routes `verified → finalize`,
`failed → recover`, anything else → `finalize`.

## Red-team report

`tests/verifier/test_redteam.py` fixes the contract and varies only the
state. Ten false-success states, zero false passes:

| # | Corruption | Verdict |
|---|---|---|
| 1 | Success with no row at all | failed |
| 2 | Replacement linked to the wrong customer | failed |
| 3 | Replacement linked to the wrong order | failed |
| 4 | Refund with the wrong amount | failed |
| 5 | Two replacements for one item | failed |
| 6 | Unrelated order inserted alongside the effect | failed |
| 7 | Ticket status never moved | failed |
| 8 | Note without a mutation key | failed |
| 9 | Refund total above paid | failed |
| 10 | Required note row removed | failed |

Correct replacement, refund, and note+status states verify; a missing
before-snapshot is `inconclusive`; an out-of-registry effect fails
closed. `tests/verifier/test_adapter.py` proves the live-DB round trip
(snapshot persists first-wins, verdict rows persist, missing snapshot
stays inconclusive).

## Manual check

Corrupt a replacement by hand (wrong customer, wrong amount, extra row)
and run verification: every corruption above returns `failed` naming the
violated invariant.
