# Durable runs (Phase 20)

**Leases.** One runner owns a task at a time: `SKIP LOCKED` claims in
`agent/runtime/lease.py`, heartbeats every 10 transitions, release on
finish. An expired lease lets another runner start a new `task_runs`
attempt; `poll_once` claims every claimable task.

**Resume.** `agent/runtime/resume.py`: completed actions resume verbatim
from the last checkpoint, interrupted reads re-run, interrupted writes
restart as unknown outcomes (probe follows). Parked approvals and
clarifications stay parked.

**Budgets** (`agent/runtime/budgets.py`, §19 numbers). Every graph edge
fails closed to `finalize` when a budget is blown; `finalize` records
`BUDGET_EXCEEDED:<name>` and the task fails safely:

| Budget | Limit |
|---|---|
| iterations | 40 |
| tool_calls | 60 |
| retries_per_action | 3 |
| total_retries | 10 |
| recovery_attempts | 6 |
| runtime_s | 300 |
| approval_wait_s | 24h |

**Cancel.** `POST /api/tasks/{id}/cancel` moves live tasks to
`cancelled` (terminal tasks answer 409); the DB trigger still enforces
the transition table.
