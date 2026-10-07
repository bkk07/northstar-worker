# Screenshots

No images are committed yet. Add PNGs to the folders below - the `README.md` references them as relative placeholders and will render once the files exist.

## Expected files

```
docs/screenshots/customer/
├── home.png              # Customer home / hero + nav
├── products.png          # Product grid
├── product-detail.png    # Single product + category/price + policies
├── cart.png              # Cart contents
├── checkout.png          # Checkout / mock payment form
├── order-tracking.png    # Order detail showing DELIVERED status
└── ticket.png            # Customer ticket conversation (AI_AGENT bubble visible)

docs/screenshots/support/
├── dashboard.png         # Queue + stats (OPEN / WAITING_FOR_HUMAN)
├── ticket-detail.png     # Ticket detail with Customer + Order context panels
├── customer-context.png  # Customer panel expanded
├── order-context.png     # Order/items/tracking panel expanded
└── approval.png          # Approval card (PENDING, countdown, Approve/Reject)

docs/screenshots/ai/
├── ai-copilot.png        # AI Copilot executing with step timeline
├── agent-progress.png    # Activity / SSE tool stream
├── tool-trace.png        # GET /trace rendered (steps + approvals + audits)
├── hitl.png              # HITL approval gating before execute
└── resolution.png        # Final RESOLVED + AI_AGENT message on customer ticket
```

## Recommended priority order (add these 9 first)

1. `customer/home.png`
2. `customer/product-detail.png`
3. `customer/order-tracking.png`
4. `customer/ticket.png`
5. `support/dashboard.png`
6. `support/ticket-detail.png`
7. `ai/ai-copilot.png`
8. `ai/hitl.png`
9. `ai/resolution.png`

## Notes

- Use 1440×900 or similar; crop browser chrome that shows secrets.
- The root `README.md` embeds `customer/home.png`, `support/ticket-detail.png`, and `ai/ai-copilot.png` as the three strongest visuals - keep those three sharp.
- Do not commit dummy 1px images to pass a check - leave the placeholder until the real capture exists.
