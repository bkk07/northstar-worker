# Threat Model (draft, Phase 23)

## Attacker

The customer: controls ticket subject/body and any page text reachable
through the browser. The operator is trusted; the model (Mercury) is
untrusted prose, never authority.

## What the attacker wants

- A payout, refund, or replacement they are not entitled to (S5/S38).
- Authority escalation: role-play, "system override", fake pre-approval.
- Scope widening: other customers' orders, blanket refunds.
- Smuggling: encoded instruction blobs in ticket bodies.

## Defenses (each mechanical, tested)

1. **Amounts from operator text only.** The compiler binds refund
   amounts from `parse_operator_amounts(task_text)`; ticket/page text
   never contributes. Traceability records the provenance.
2. **Bindings from database reads.** Codes resolve through read tools;
   ownership cross-checks park mismatches; look-alike names park.
3. **Trusted-facts boundary.** Policy facts keep IDs, linkage,
   statuses, and money; free text is dropped at load.
4. **Policy decides, LLM proposes.** Eligibility, ownership,
   duplicates, and caps are deterministic; S5 BLOCKs above the cap.
5. **Memory provenance.** Every item needs a source and trust; page
   data stays untrusted; cross-checks mint separate trusted items.
6. **Injection flags.** Deterministic patterns mark role-play,
   overrides, authority claims, payout directives, scope widening,
   and encoded blobs. Flags audit; they never authorize.
7. **Commit tokens.** Submits need HMAC tokens over the exact payload;
   approvals are single-use, hash-bound, and expiring, with no
   auto-approve path.
8. **Independent verifier.** Even a fully fooled worker cannot report
   done without the real database state matching the contract.

## Residual risks

- Mercury latency/flakes under load (operational, not security).
- Novel phrasings the detector misses: contained by 1–5 and 7–8,
  which do not depend on detection.
- Operator error at the approval queue: bounded by single-use,
  hash-bound, expiring approvals.
