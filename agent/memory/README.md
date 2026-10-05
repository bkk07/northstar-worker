# memory

Run-scoped working memory with provenance plus injection defense
(Phase 23): `store.py` (sourced writes, trust reads), `provenance.py`
(source trust map), `envelope.py` (untrusted wrapping, bounded prompt
blocks), `injection_detector.py` (deterministic flags). Items are
written only by `observe` and `contract`, never from LLM free text.
