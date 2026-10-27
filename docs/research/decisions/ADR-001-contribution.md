# ADR-001 — Research contribution

- **Status:** Accepted (team), pending guide sign-off
- **Date:** 2026-10-27
- **Decider:** P4 (Bhavish), reviewed by P1
- **Supersedes:** the H1/H2 sketch in `docs/phase-0/01-research-plan.md §4`

## Context

The brief requires a defensible contribution and forbids claiming originality merely for
combining existing components. The survey (30 records, `docs/research/papers/`) and the gap
matrix show the pipeline itself is standard, and that four capability columns are empty
across every surveyed system: source-reliability weighting, calibration, abstention, and
uncertainty-driven compute allocation.

## Decision

The claimed contribution is **evidence-aware, calibrated, abstention-capable claim
verification**, scoped as in `novelty-statement.md`, decomposed into H1a, H1b, H1c and H2 —
each with a stated falsification criterion fixed before any experiment is run.

The secondary contribution is the **six-status scheme plus the `verifact-stress` evaluation
set**, which stands independently of the hypotheses.

## Consequences

- Phase 10 must implement Baselines A–D and the four ablations, or the contribution is
  unsupported and must be withdrawn from the report.
- Thresholds and the calibrator are fitted on **dev** and frozen, with the freeze commit hash
  recorded, before test is touched once.
- Every `Verdict` must carry its component scores, or H1a and H1b cannot be analysed.
- The report's Literature Survey must explicitly state that the pipeline shape, decomposition,
  retrieval+NLI, correction and KG verification are all prior work, with citations.
- If a targeted search on source-credibility-aware verification or selective prediction finds
  prior work covering columns 5–7, this ADR is amended and the claim narrowed. The team is
  required to run that search before the report is finalised (gap-matrix.md, threat 2).

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| "Novel multi-stage hallucination detection pipeline" | The pipeline is Guo et al.'s. Claiming it would be false and is the most likely thing to collapse under questioning. |
| Self-consistency detection (SelfCheckGPT-style) as the core | Measures agreement, not support; cannot cite evidence or correct; needs access to the original generator, which a downstream verifier does not have. |
| Train a learned aggregator (KGAT-style) | Needs FEVER-scale supervision, loses the per-component transparency the brief requires, and gives us a black box to defend instead of a formula. |
| LLM-as-judge for verdicts | Puts an unauditable, uncalibrated model in the decision path, and makes results non-reproducible. Rejected on principle, not cost. |
