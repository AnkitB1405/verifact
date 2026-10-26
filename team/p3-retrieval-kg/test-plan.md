# Test Plan — P3 — Evidence & Knowledge Graph Engineer

Scope: unit tests for the modules you own, plus the adversarial cases listed here.
Integration and API tests are P1's; you contribute fixtures to them.

| Area | Tests |
|---|---|
| registry | unknown source → lowest tier with a log line, not dropped; tier values load correctly |
| SSRF | `http://127.0.0.1`, `http://169.254.169.254`, `http://[::1]`, a hostname resolving to a private IP, an off-allowlist redirect, an oversized response, a hanging host — all blocked |
| clients | recorded-response fixtures so CI needs no network; cache hit/miss; timeout path |
| bm25/dense | known-item retrieval on a tiny fixed corpus; RRF ordering is deterministic |
| retrieval | Recall@{1,5,10} on a FEVER dev subset — **measured and recorded**, not asserted |
| entity linking | ambiguous mention returns ≥2 candidates; no-candidate case handled |
| kg | absent relation → `MISSING` (never `CONTRADICTED`) |
| kg | contradicting relation → `CONTRADICTED` with the path as evidence |
| kg | unsupported relation type → `NOT_APPLICABLE` |
| kg | subgraph node cap and build-time bound respected |
| offline | full retrieval path with network disabled |

## Measured, not asserted

Any quality number (F1, Recall@k, FPR, ECE) is **recorded with the run that produced it**, in
`docs/testing/test-report.md`. Tests assert "the pipeline runs and the shape is right"; tests
do **not** assert a quality threshold we tuned to pass.

## Fixtures you own

## Known untested areas (be honest — this goes in Known Limitations)
