# How to add a task (Phase 28)

New workflows land **outside the frozen core** (`agent/graph`,
`agent/nodes`, `agent/failures`, `mcp_server/tools`, `browser/`).
Follow these steps; each one is checked by a test.

## 1. Describe the scenario

Add a row to the catalog (`eval/scenarios/catalog.yaml`, or
`eval/held_out/catalog.yaml` for sealed scenarios):

- `id`: next `S<number>` (seeded, below S901) or `S901+` (held-out).
- `task`: the operator text, with real codes (ticket, order).
- `facts`: the oracle inputs (`amount_paise`, `ownership_ok`,
  `ambiguous`, `unsupported`, `injection`, `refunds_last_90d`,
  `item_value_paise`).
- `intended_effects` / `expected_effects`: registry effects only
  (`replacement.create`, `refund.create`, `ticket.note`,
  `ticket.status`, `ticket.reply`).
- `fault_plan`: optional `{type, target, trigger}` for recovery arcs.

Run the oracle check: expectations must equal
`derive_expected(scenario, intended_effects, thresholds)` —
`tests/eval/test_catalog.py` (and `test_held_out.py`) fail loudly on
typos. If you edited the held-out file, recompute its seal
(`eval.generalization.seal_catalog` → `SEALED_SHA256`).

## 2. Seed the entities

Add the customers (`Cxxx`), orders (`ORD-xxxx` with items), and
tickets (`TCK-xxx` with bodies) to `database/seeds/*.yaml`, then
`POST /api/control/seed` (or the seed service). `check.py` enforces
reference integrity (ticket → customer/order, order → customer).

## 3. Extend outside the core, if needed

- New effect shape → effect registry entry (type, capability,
  verification invariant, policy rule).
- New policy rule → isolated section in `agent/policy/rules.py`
  (never edits to existing rules in the same commit).
- New verifier invariant → isolated per-effect module.
- Log every extension in the eval/generalization report under
  "Task-specific extensions".

Core edits are forbidden without a freeze-tag exception: `core_diff`
in `eval/generalization.py` counts lines since `eval-core-freeze`,
and `tests/eval/test_generalization.py` fails on any nonzero count.
Genuine bug fixes go through the same gate — counted, documented,
one per commit.

## 4. Run it

```bash
python eval/eval.py --scenarios S916 --suite smoke
```

Answer the four questions: did it resolve/park/block as oracled, did
policy name the right rule, did the verifier agree with the state,
did anything commit that should not have? Record the run
(`--record`) so `/evaluation` shows it.
