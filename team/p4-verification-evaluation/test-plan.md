# Test Plan — P4 — Verification, Scoring & Research Engineer

Scope: unit tests for the modules you own, plus the adversarial cases listed here.
Integration and API tests are P1's; you contribute fixtures to them.

| Area | Tests |
|---|---|
| similarity | monotonic on a paraphrase/unrelated pair set |
| nli | label mapping asserted against known entail/contradict/neutral examples; premise/hypothesis direction tested (reversing it changes the result) |
| weighting | high-tier recent source outweighs low-tier old one; weights sum/normalise correctly; zero-evidence case does not divide by zero |
| aggregate | **each of the six statuses is reachable** by a constructed fixture |
| aggregate | no evidence → `UNVERIFIABLE`, never `CONTRADICTED` ← the project's defining test |
| aggregate | conflicting high-E/high-C sources → `AMBIGUOUS` |
| aggregate | KG `MISSING` cannot flip a supported claim to contradicted |
| calibrate | ECE improves on dev after fitting; unfitted calibrator → `calibrated=False` |
| budget | escalation triggers fire on uncertain/numeric/temporal claims; `budget_spent` recorded |
| explain | explanation text names the component that decided the status |
| harness | one command reproduces every table; same seed → same numbers; config hash recorded |
| baselines | A/B/C share the proposed system's interface and are run on identical splits |

## Measured, not asserted

Any quality number (F1, Recall@k, FPR, ECE) is **recorded with the run that produced it**, in
`docs/testing/test-report.md`. Tests assert "the pipeline runs and the shape is right"; tests
do **not** assert a quality threshold we tuned to pass.

## Fixtures you own

## Known untested areas (be honest — this goes in Known Limitations)
