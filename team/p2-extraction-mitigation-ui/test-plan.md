# Test Plan — P2 — NLP Input, Mitigation & Frontend Engineer

Scope: unit tests for the modules you own, plus the adversarial cases listed here.
Integration and API tests are P1's; you contribute fixtures to them.

| Area | Tests |
|---|---|
| input | offset invariant: `text[s.char_start:s.char_end] == s.text` for every sentence, over a property-based set |
| input | empty / whitespace / 1-char / max-length / non-ASCII / mixed-newline inputs |
| extraction | 50-sentence hand-annotated dev set → entity/date/number F1 reported, not asserted-perfect |
| extraction | compound-sentence decomposition cases; pronoun resolution failures documented |
| extraction | opinion/rhetoric set (60 items) → check-worthiness FP/FN rates recorded |
| extraction | LLM path: truncated JSON, wrong schema, empty response → falls back to rules, logs, never raises |
| mitigation | every produced correction cites ≥1 passage, and re-verification of the correction is not CONTRADICTED |
| mitigation | insufficient evidence → `abstained=True` with a reason; no text invented |
| mitigation | annotated text spans align with original offsets |
| frontend | client types compile against the committed OpenAPI; one smoke test of the happy path |

**Adversarial cases you own (prompt injection):** evidence passage containing
"ignore previous instructions", a fake system prompt, a request to output a different verdict,
an instruction to drop the citation, a passage containing an API-key-shaped string, and
instructions hidden in a URL or title field. All must leave the verdict unchanged. Document
each in `tests/security/test_prompt_injection.py` with a comment naming the attack.

## Measured, not asserted

Any quality number (F1, Recall@k, FPR, ECE) is **recorded with the run that produced it**, in
`docs/testing/test-report.md`. Tests assert "the pipeline runs and the shape is right"; tests
do **not** assert a quality threshold we tuned to pass.

## Fixtures you own

## Known untested areas (be honest — this goes in Known Limitations)
