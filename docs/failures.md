# Failure taxonomy (Phase 17)

One failed tool call → exactly one type. First match wins, in this order.

| Type | When | Retry as-is |
|---|---|---|
| `policy_blocked` | Token/capability denial | no (operator/policy) |
| `guard_violation` | URL-guard breach (agent bug) | no |
| `session_expired` | 401 / login redirect / session revoked | yes, after re-login |
| `forbidden` | 403 | no |
| `not_found` | 404 | no |
| `conflict_duplicate` | 409 / active-duplicate message | no (reconcile) |
| `validation_error` | 422 | no (fix params) |
| `stale_reference` | Page moved since observed | yes, re-observe first |
| `element_not_found` | Unknown ref (removed field) | yes, re-observe first |
| `dom_drift` | Banner / removed-field markers | yes, re-observe first |
| `timeout` | Timeouts on reads | yes |
| `network_error` | 5xx on reads, transport errors | yes |
| `unknown_outcome` | Any failure on `browser_submit` (500, timeout, exception) | **never** — probe, then reconcile |
| `browser_unavailable` | Session crashed / target closed | yes, reopen |

Pins: write + 500 → `unknown_outcome`; read + 500 → `network_error`;
redirect → `session_expired`. Attempts carry the type in
`action_attempts.error_type`; classifications land in audit as
`failure.classified`.
