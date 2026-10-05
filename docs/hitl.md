# Human Approval and Clarification (Phase 22)

Eligibility is not authorization: some commits need a real human, and
some tasks need a real answer, before the worker may proceed.

## Approval flow

```
policy HUMAN_APPROVAL -> approvals row (pending) + checkpoint
 -> task WAITING_FOR_APPROVAL, runner releases the lease
 -> GET /api/approvals shows action, params, reason, rule
 -> POST /api/approvals/{id}/approve|reject -> task requeued to running
 -> resume at human_approval -> approved consumes into a commit token
 -> execute -> observe -> verify
```

- Requests bind (task, action, params payload hash) and expire after
  `max_approval_wait` (24h). Overdue rows flip to `expired` on every
  read path (the expiry sweep); decisions on non-pending rows 409.
- Consumption is single-use (`approved` to `consumed`): replays,
  expired rows, and changed params never yield a token.
- Reject requeues and the graph finalizes BLOCKED with no mutation.
- There is no auto-approve path: `approved` is written only by the
  operator endpoint (`tests/architecture/test_no_auto_approve.py`
  pins the single write site; the agent only consumes).

## Clarification flow

- Ambiguous contracts park an operator clarification; the answer
  re-enters the compiler on resume (`answered -> contract`).
- Customer-information requests park distinctly: the task goes
  `WAITING_ON_CUSTOMER` until a reply is observed, the operator
  answers, or the 24h TTL expires the wait (inconclusive, never a
  guess). Ticket status moves stay in the normal effect flow.
- Answers are single-use (409 on replay) and requeue the task.

## Waiting across restarts

Parked runs end the graph cleanly with their WAITING state; the next
claim starts a new attempt that resumes from the checkpoint. The
checkpoint plus the journal is the whole story — no in-memory wait
state exists to lose.

## Manual check

Pause a held commit, approve through curl, and watch the resume
consume into a token and continue to verification.
