# Planning and decision (Phase 14)

Goal-directed behavior without per-task code: the same prompt, checks,
and loop serve every workflow in the effect registry.

## Plan (`PlanningService`)

Contract → ordered steps over registered tools, proposed by Mercury 2.5
(`plan` prompt) and shape-checked here: the contract must be `ok`, steps
non-empty, every tool registered. Steps land in checkpoint state
(`plan`, `cursor`); violations are `PlanningError`, not runtime retries.

## Decide (`DecisionService`)

One typed action from plan position, working memory, the last
observation, and the validator's last error. The brief always carries a
`Correction:` block when the previous proposal was rejected, so the
model fixes exactly that.

## Validate (`action_validator` + `ValidationService`)

Four gates, first failure wins, all errors correctable:

1. **Schema** — a real `NextAction` (tool, params, rationale).
2. **Known tool** — mirrored from the MCP registry (parity-tested).
3. **Capability** — the tool's capability (or the submit effect) is in
   the contract's scope.
4. **Binding** — submit bindings equal the locked contract exactly;
   reads need well-formed refs only, so discovery stays possible.

Accepted proposals reserve their `worker.actions` row as `proposed`
(execution moves it in Phase 16). Rejected ones return to `decide` with
the error and a bumped count.

## The loop always terminates

- `decide` falls back to harmless `browser_observe` after
  `MAX_VALIDATION_ROUNDS` (3) failed corrections — no more LLM calls.
- `route_validate` ends runs whose failures somehow pass 5 anyway.

Preview anything without executing: `python scripts/dry_run.py "<task>"`.
