# Browser layer — perception notes (Phase 10)

Everything the worker does in the world goes through this package:
one Chromium context per run, accessibility perception, guarded actions.

## Perception model

`observer.observe(page)` returns an `Observation`:

- Refs `e1…eN` are **ephemeral handles**, rebound on every observation.
  A ref is `(kind, role, name, value, form)` where kind is one of
  `role` (role + accessible name), `label` (associated label text), or
  `text` (visible text fallback).
- `page_version` is a hash over URL + interactive structure (tag, role,
  name). Renames, reorderings, and added/removed controls change it;
  pixel changes and timestamps do not.
- The snapshot **settles first**: two identical frames in a row (lazy
  chunks and loaders finish before refs bind). Actions never target a
  half-rendered tree.
- `find(role, name, form)` filters by role equality, name substring, and
  enclosing labeled form — sibling forms with identical labels (the
  replacement vs refund forms on a ticket page) stay unambiguous.

## Action contract (`session`)

- `click(ref)` / `fill(ref, value)` resolve through `locators.resolve`
  (accessibility queries only — no CSS/XPath anywhere) and require
  **exactly one** match, else `ElementNotFound`.
- Actions accept the `page_version` the refs came from; a mismatch raises
  `StaleReference` before touching the page. Detached elements map to the
  same error; per-action timeouts map to `ActionTimeout`.
- `navigate(path)` pre-checks the URL guard (`GuardViolation`), so
  `/worker`, `/evaluation`, `/api/control/*`, and off-origin targets never
  even issue a request. A route-level guard aborts them as backstop.
- `network.last_status("/api/ops/...")` reports the captured HTTP status
  of the commit — the agent reasons from captured traffic, never toasts.
- Storage state persists per run id (`SessionManager`); a runner restart
  resumes the same `/ops` session.

## Failure surfaces honored

The `/ops` UI deliberately reuses labels across forms and remounts under
the `stale_rerender` flag. The layer answers with strict resolution
(refuse ambiguous refs) and version enforcement (refuse stale refs) —
recovery (re-observe, re-discover) is the agent's job in Phases 17–18.
