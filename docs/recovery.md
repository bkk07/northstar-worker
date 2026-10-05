# Recovery strategy table (Phase 18)

Failure type → strategy (bounds in parentheses; hits terminate the run).

| Failure | Strategy | Then |
|---|---|---|
| `network_error` | `retry` (3, exponential backoff 0.5s→5s) | `execute` same action |
| `timeout` | `retry` (3, backoff) | `execute` same action |
| `stale_reference` | `re_observe` (3) | `observe` rebinds refs |
| `element_not_found` | `fallback_tool` (2) | dead UI search → `api_get` |
| `dom_drift` | `re_discover` (2) | `observe` fresh, ref dropped |
| `session_expired` | `re_observe` (2, `relogin: true`) | `observe` on a reopened session |
| `validation_error` | `re_observe` (2) | `decide` corrects with the 422 context |
| `not_found` | `re_discover` (2) | `observe` fresh |
| `browser_unavailable` | `re_observe` (2) | `observe` on a reopened session |
| `forbidden`, `policy_blocked`, `guard_violation` | `terminate_safely` | `finalize` (no blind retry, no duplicates) |
| `conflict_duplicate`, `unknown_outcome` | `probe` (2) | `probe_reconcile`: adopt, same-key retry, or park (Phase 19) |

Fallbacks stay inside the contract's `read.fallback` scope; outside
scope they degrade to `terminate_safely`. Every round emits
`recovery.decided` with counters. Unknown-outcome probe arrives in
Phase 19.
