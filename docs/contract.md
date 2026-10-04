# Task contract spec (Phase 13)

The contract is the deterministic work order between an LLM proposal and
everything downstream: policy scope, MCP capabilities, and verification.
The LLM proposes (`Interpretation`); code disposes.

## Pipeline

```
operator text → UnderstandingService (Mercury 2.5, `understand` prompt)
  → resolve_entities (read tools only: customer search, shop reads by code)
  → parse_operator_amounts (Rs./₹/INR in the operator text, paise ints)
  → compile_contract (pure) → persist `worker.task_contracts`
```

## Status (drives the graph edge)

| Status | Meaning | Graph |
|---|---|---|
| `ok` | Bound IDs, schema-valid params, traced amounts | → `plan` |
| `ambiguous` | Needs the operator (multi-match, scope, conflict) | → `clarification` |
| `unsupported` | No registry mapping | → `finalize` (INCONCLUSIVE) |

## Binding rules

- Codes (`C102`, `ORD-1942`, `TCK-101`) are scanned deterministically
  from the operator text — never taken from the LLM on trust.
- `C102` binds via customer search (exact code); `ORD-1942` / `TCK-101`
  via the code-addressable shop reads. The order's own customer binds
  when no code names one.
- Names bind on a unique search hit; zero or several hits park with a
  question (look-alikes are never guessed).
- Customer/order/ticket triples must agree on ownership; conflicts park.
- Cancellations with a bound ticket but no clear effect park on scope
  ("full order or single item?"); anything else unmappable is
  `unsupported`.

## Amounts

Every `amount_paise` must equal one parsed from the operator text.
Ticket/page figures can never enter a contract (`UntraceableAmountError`
otherwise); zero or several operator amounts park for clarification.
Refunds above policy thresholds still compile — HUMAN_APPROVAL vs ALLOW
is the policy engine's call (Phase 15), not the contract's.

## Effects and capabilities

Each effect is validated against its registry `expected_schema`
(`agent/contract/effect_registry.py`). Capabilities are derived:
`read`, `read.fallback`, `probe`, `browser`, plus one submit capability
per effect. `snapshot_scope` (bound customer/order/ticket IDs) tells the
verifier what the run may touch (Phase 21).
