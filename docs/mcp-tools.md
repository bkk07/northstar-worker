# MCP tool catalogue (Phase 11 — generated from `mcp_server/registry.py`)

Typed boundary the agent can never bypass. Reads go through `GET`-only
HTTP; writes go only through the hosted browser behind a signed policy
token. The control plane, shell, SQL, and filesystem are absent by
construction (asserted by `test_tool_catalogue_matches_registry`).

Error prefixes: `capability_denied`, `token_denied`, `not_found`,
`rejected` (allowlist), schema errors for malformed calls.

| Tool | Capability | R/W | Side effect | Idempotency | Failure modes |
|---|---|---|---|---|---|
| search_customer | read | R | none | n/a | empty, multi-match (data) |
| get_customer | read | R | none | n/a | not found |
| search_order | read | R | none | n/a | not found |
| get_order | read | R | none | n/a | not found |
| get_ticket | read | R | none | n/a | not found |
| get_policy | read | R | none | n/a | not found |
| api_get | read.fallback | R | none | n/a | non-allowlisted path → rejected |
| inspect_state | probe | R | none | n/a | unknown kind |
| browser_open | browser | R | creates session | reuses session | session expired, timeout |
| browser_navigate | browser | R | navigation | n/a | URL guard rejection |
| browser_observe | browser | R | none | n/a | stale page |
| browser_click | browser | R* | page state only | n/a | stale ref, not found |
| browser_fill | browser | R* | form state only | n/a | not found, validation |
| browser_submit | per effect | W | commits | key + probe + DB unique | 500/timeout/validation/duplicate data; valid ALLOW token required |
| browser_back | browser | R | none | n/a | none |
| browser_screenshot | browser | R | file | n/a | none |

`*` Click and fill commit nothing. Only `browser_submit` on an effect form
is a commit: it checks the task's `browser` + effect capabilities, verifies
the HMAC token over the exact params, confirms the ref sits in the matching
form (or its confirm dialog), injects the `Idempotency-Key`, and returns the
captured HTTP status for the agent to classify.

Every browser act serves a fresh observation and enforces staleness: calls
made without observing the current page fail instead of acting on old refs.
