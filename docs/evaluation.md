# Evaluation (draft — Phase 9)

Full harness in Phase 27. This draft records the fault catalogue: every
chaos fault, what it does, which scenario covers it, and what recovery it
exercises (recovery logic arrives Phases 17–19).

## Arming faults

```powershell
$headers = @{ Authorization = "Bearer local-operator-token" }
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/control/chaos -Method POST `
  -Headers $headers -ContentType "application/json" `
  -Body '{"fault_type":"HTTP_500_AFTER_COMMIT","target":"ops.replacements",
    "trigger":{"nth_call":1},"params":{}}'
```

Plans live in `biz.fault_plans` (`armed`, `calls`, `consumed_at`).
Firing faults are consumed once; `POST /api/control/reset` clears them.
`GET /api/control/oracle/S1` (or a ticket code) returns the independent
expectation for one scenario.

## Fault catalogue (§27)

| Fault | Behavior | Scenario | Recovery exercised (later) |
|---|---|---|---|
| HTTP_500_BEFORE_COMMIT | 500, nothing written | S22 | Retry reads; probe-then-retry writes |
| HTTP_500_AFTER_COMMIT | Row committed, then 500 | S6 | Probe finds row → reconcile, no resubmit |
| TIMEOUT | Response delayed past client deadline (`params.delay_seconds`, `after_commit`) | S23 | UNKNOWN_OUTCOME → probe → reconcile/retry |
| STALE_ELEMENT | Queue remounts (`stale_rerender` flag) | S24 | Re-observe, re-discover refs |
| REMOVED_SEARCH_FIELD | Search input absent (`removed_search_field`) | S7 | Fall back to read API |
| DOM_DRIFT | Labels renamed, fields reordered (`dom_drift`) | S25 | Re-discover by role, re-plan interaction |
| VALIDATION_ERROR | First submit 422s with a field error | S10 | Correct from facts, resubmit same key |
| DUPLICATE_EFFECT | Idempotency key ignored once (409 on replay) | S8 | Probe finds existing → reconcile |
| SESSION_EXPIRY | Sessions revoked, calls 401 | S9 | Re-login, resume same step |

UI-flag faults stay armed until reset (they are read on every page load);
firing faults consume on their nth matching call.
