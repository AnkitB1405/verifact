# P4 — Verification, Scoring & Research Engineer

**Member:** <<TBD: name / roll no>>
**Epics:** 1 (Research & Requirements), 6 (Verification Engine), 7 (Scoring + Explanation), 10.1–10.5 (Evaluation)

> Read `docs/phase-0/04-work-division.md` first. This file is the detail for one role.

## 1. Files you own (primary)

- `src/verifact/verification/{similarity,nli,weighting,aggregate,calibrate,engine}.py`
- `src/verifact/orchestrator/budget_policy.py` (adaptive compute)
- `src/verifact/explain/assembler.py`
- `eval/harness.py`, `eval/baselines/{a_similarity,b_nli,c_retrieval_nli}.py`, `eval/ablations/`
- `eval/datasets/verifact_stress/` (curation lead)
- `docs/research/**`, `docs/testing/test-report.md` (results sections)

## 2. What you consume from others

- `claims_golden.json` (P2), `evidence_golden.json` + `kgcheck_golden.json` (P3).
  **All your aggregation tests run on fixtures** — never on live retrieval.
- Source reliability tiers from P3's `registry.yaml`.

## 3. What others consume from you (your blocking deliverables)

- The 6-status decision rule and the aggregation formula — P1 encodes the enum, P2's UI
  renders it, the report's central chapter is yours.
- Calibrated confidence + ECE. The `calibrated` flag must be honest.
- **Every measured number in the report.** You are the person who must refuse to publish a
  number that was not produced by a committed run.

## 4. Your specific risks

- You carry the research risk. If H1 does not hold, the honest outcome is a negative result
  plus the explainability/abstention framework — plan for that now so it is not a crisis in
  Sprint 7. Write the "if H1 fails" paragraph in Sprint 1.
- Threshold tuning on test data would invalidate the entire evaluation. Tune on **dev**, freeze,
  then touch test once. Record the freeze commit hash in `docs/testing/test-report.md`.
- Presenting an uncalibrated softmax score as "probability the claim is true" is the single
  most likely substantive criticism in the viva. Guard against it in code *and* in wording.
- NLI model size depends on available compute (`<<TBD: GPU?>>`). Have a CPU-viable default.

## 5. Your gate obligations

- Gate 0: 6 status definitions frozen; ADR-001 draft.
- Gate 1: 18+ paper records, gap matrix, novelty statement; similarity + NLI working.
- Gate 2: aggregation producing all six statuses on fixtures; explanations readable.
- Gate 3: calibration + ECE; adaptive budget with `budget_spent` recorded.
- Gate 4: baselines + main tables + ablations + error analysis, all reproducible by one command.

## 6. Your Definition of Done (in addition to the team DoD)

- Unit tests for your own logic — nobody else writes tests for your module.
- `docs/design/<your module>.md` updated in the same PR as the code.
- Three bullets in `explainer-log.md` per merged story.
- If you changed `contracts/`, the golden fixture you own is regenerated in the same commit.
- No number in your report sections that is not backed by a committed run.
