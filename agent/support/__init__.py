"""Phase 8 AI support agent (spec Phase 8): supervisor + specialized workflows.

The agent solves customer tickets across REFUND / REPLACEMENT / RETURN /
CANCELLATION / ORDER_STATUS / DELIVERY / PAYMENT / GENERAL_QUERY by calling
the Phase 7 business tools (local calls, never raw SQL) and the Groq-backed
LLM client for classification and reply drafting.

No live calls happen without an explicit client: every entry point accepts
`llm=None` (deterministic keyword classifier + template replies) and an
injectable `tools` map, so unit tests run fast with fakes and never touch
a model. Approval pauses (`approval_required`) are consumed by Phase 9 HITL.
"""
