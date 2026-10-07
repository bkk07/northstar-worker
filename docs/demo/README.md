# Demo

## Video

- Final published URL: `ADD_VIDEO_URL` — replace the placeholder in `README.md#demo-video`.
- Local file (git-ignored or committed at your discretion): `docs/demo/demo.mp4`
  - If you commit it, link it with a relative path: `./demo.mp4` from this folder.
  - Do not generate a fake video here.

## What to record

Follow `README.md#running-the-demo` exactly:

1. Customer :5174 signup → browse → cart → checkout → wait ~60s → DELIVERED
2. Raise ticket TKT-XXXXXX ("My headphones arrived damaged. I want a replacement.")
3. Support :5175 login as `admin@northstar.shop` / `admin`
4. Open the ticket → **Solve with AI** → watch trace → approve HITL when shown
5. Verify `GET /support/tickets/:id/trace` and the `AI_AGENT` message on the customer ticket

## Checklist before publishing

- [ ] `INCEPTION_API_KEY` set so narration is natural (draft fallback is expected otherwise)
- [ ] Seed hash printed by `scripts/seed.sh` is visible if evaluator asks to reproduce
- [ ] No secrets audible/visible in the recording
