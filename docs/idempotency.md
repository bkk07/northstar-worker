# Idempotency design (Phase 19)

Five layers, outermost first:

1. **Deterministic mutation identity.** `key_for(task, tool, binding params)`
   (`agent/runtime/mutation_keys.py`) — stable across retries and resumes;
   refs and tokens are stripped before hashing. Sent as `Idempotency-Key`.
2. **DB constraints.** `UNIQUE(mutation_key)` plus active-row partial uniques.
3. **Search-before-create.** Every submit probes business identity first;
   an existing row is adopted (`reconciled`, zero attempts), never recommitted.
4. **Probe-before-retry.** A failed commit → `unknown_outcome` → probe by key,
   then identity: match adopts (`RECONCILED_EXISTING`), foreign rows park
   `INCONCLUSIVE` (`probe_status: mismatch`), absent retries **once** with
   the same key, unreadable probes get 3 rounds then park.
5. **Verifier.** Catches a duplicate even if layers 1–4 all fail (Phase 21).

Same-key retries make blind resubmits safe (layer 2 turns them into
replays); the `duplicate_effect` fault is therefore absorbed by the
probe, never by luck. Journal states for submits: `proposed → started →
done | failed | reconciled`.
