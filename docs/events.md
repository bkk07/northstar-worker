# Worker event contract (Phase 25)

One audit row is one event. `GET /api/tasks/{id}/events` streams them
as SSE; `GET /api/tasks/{id}/events/history` replays them as JSON.
Both order by the gapless `seq`; both carry the same fields.

## Frame

```text
id: 42
event: audit
data: {"seq": 42, "kind": "policy.decision", ...}

```

- `id` is the row's `seq` — `Last-Event-ID` resume is exact, and
  replay (`history`, or backfill after a sequence) converges with the
  live tail on `seq > last_yielded`, so reconnects neither miss nor
  duplicate.
- `event` is always `audit` (one event type; `kind` varies in data).
- `data` is the full audit row: `id`, `task_id`, `run_id`, `seq`,
  `ts`, `node`, `tool`, `kind`, `status`, `error_type`,
  `retry_count`, `duration_ms`, `policy_result`,
  `verification_result`, `payload`.
- Idle streams ping with `: ping` comments (15s) so proxies keep
  the connection; clients ignore comment lines.

## Transport

- Postgres `LISTEN/NOTIFY` on channel `worker_audit_events`
  (migration `0006_audit_notify`): the trigger shouts
  `<task_id>:<seq>` at commit, so listeners never see uncommitted
  rows. Payloads stay tiny; subscribers fetch the row by
  `(task_id, seq)`.
- One daemon listener per backend process routes wakeups to
  per-stream queues; disconnects unregister their queue.
- Auth travels in the session cookie (same-origin). The handshake
  needs no credentials and sets none — no token in the URL, no
  token in the bundle (`useEventSource` takes a bare relative URL).

## Kind catalog

| kind | node | meaning |
|---|---|---|
| `run.start` / `run.end` / `run.error` | — | run lifecycle (`run.end` carries terminal status) |
| `run.packet` | — | terminal packet persisted (cites `evidence_id`, headline) |
| `node.transition` | every node | uniform visit (delta keys + run status in payload) |
| `contract.compiled` | contract | contract status + effect count |
| `policy.decision` | policy_check | outcome, deciding rule, reason |
| `tool.call` | execute | tool + action/mutation keys |
| `failure.classified` | classify | failure type + signals |
| `recovery.decided` | recover | strategy + counters |
| `recovery.probe` | probe_reconcile | commit-outcome verdict |
| `verification.result` | verify | independent verdict |
| `approval.park` / `.resume` / `.rejected` / `.expired` | human_approval | HITL transitions |
| `clarification.park` / `.answered` / `.expired` | clarification | clarification transitions |

## Frontend

`shared/hooks/useEventSource(url)` (typed): opens the exact URL it
is given, appends parsed `audit` frames, tracks `lastEventId` and
connection status, and closes on unmount. No UI is built on it yet
(Phase 26).
