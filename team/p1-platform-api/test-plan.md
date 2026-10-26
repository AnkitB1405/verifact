# Test Plan — P1 — Platform, API & Release Engineer

Scope: unit tests for the modules you own, plus the adversarial cases listed here.
Integration and API tests are P1's; you contribute fixtures to them.

| Area | Tests |
|---|---|
| contracts | round-trip serialise/deserialise for all 11 models; rejected invalid payloads |
| config | missing required env → startup failure with a clear message, not a 500 at runtime |
| db | `alembic upgrade head` then `downgrade -1` on a clean DB in CI |
| orchestrator | one stage raising does not lose the other claims' results; partial run recorded |
| api | every endpoint: happy path, validation error, auth failure, rate limit (429), oversized input |
| errors | no traceback or input text in any response body |
| logging | redaction filter strips raw input text at INFO |
| security | bandit/pip-audit/gitleaks/Trivy in CI; findings triaged in `docs/security/findings.md`, not suppressed |

**Adversarial cases you own:** oversized payload, deeply nested JSON, unicode normalisation
abuse, SQL metacharacters in input text (must be inert via ORM), missing/invalid API key.

## Measured, not asserted

Any quality number (F1, Recall@k, FPR, ECE) is **recorded with the run that produced it**, in
`docs/testing/test-report.md`. Tests assert "the pipeline runs and the shape is right"; tests
do **not** assert a quality threshold we tuned to pass.

## Fixtures you own

## Known untested areas (be honest — this goes in Known Limitations)
