# ADR-005 — Confidence calibration and threshold-selection protocol

- **Status:** Accepted · **Date:** 2026-10-29 · **Owner:** P4 (Bhavish) · **Reviewed by:** P1

## Context

Stage S5 produces `E` and `C` (weighted entailment and contradiction) and must emit a
confidence. The naive choice is to report `|E − C|`, or worse, the NLI model's softmax output,
as "the probability the claim is true". `guo2017calibration` establishes that modern network
confidences are not calibrated probabilities, and the brief explicitly forbids presenting an
uncalibrated model probability as a statistically meaningful one.

There is a second, subtler trap. If the decision thresholds (τ_cov, τ_weak, τ_sup, τ_con) are
chosen by looking at test performance, every reported metric is optimistically biased and the
evaluation is worthless — a failure that is invisible in the results table and fatal under
questioning.

## Decision

**1. Calibration.** `confidence` = `|E − C|` mapped through a calibrator fitted on a held-out
dev split. Default **temperature scaling** (one parameter, per `guo2017calibration`);
**isotonic regression** available via `verification.calibration.method`. The fitted calibrator
is stored as an artifact with the config hash of the run that produced it.

**2. Honesty flag.** `Verdict.calibrated` is `True` **only** when a fitted calibrator was
actually loaded. With no calibrator — a fresh checkout, a changed model, the `lexical`
fallback backend — the raw score is returned with `calibrated=False`, and the API and
dashboard must label it "uncalibrated score" rather than a probability. The flag is set from
whether the artifact loaded, never passed in by a caller.

**3. Reported metric.** Expected Calibration Error with 10 equal-width bins, reported
**before and after** calibration, on test. If ECE does not improve, H1c is falsified and we
report that.

**4. Threshold protocol.** Binding:

- Data is split train/dev/test by claim with a fixed seed; the split file is committed.
- τ_cov, τ_weak, τ_sup, τ_con and the calibrator are selected **only** on dev.
- Thresholds are then written into `config/thresholds.yaml` and the commit hash of that
  freeze is recorded in `docs/testing/test-report.md`.
- **Test is evaluated once, after the freeze.** If we later change a threshold, the test
  numbers are discarded and re-run, and the report says the evaluation was repeated.
- Baselines A–D get the same dev-tuning budget, so the comparison is fair. A baseline that is
  left untuned while the proposed system is tuned is a rigged experiment.

## Consequences

- One scalar to fit, negligible compute, trivial to explain in the viva.
- A dev split large enough to fit a calibrator is needed. With `verifact-stress` at ~120
  items, dev is small and the calibrator will be noisy — a stated limitation, and the reason
  FEVER dev is used for the main calibration fit.
- Temperature scaling corrects average confidence, not per-group miscalibration. We therefore
  **also** report ECE separately for numeric and temporal claims, because those are where we
  expect it to be worst, and a single global ECE would hide it.
- `calibrated=False` paths must be handled by the UI and the report, not treated as an error.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Report raw `\|E − C\|` as a probability | the specific thing the brief forbids, and the most obvious attack on the project |
| Ask an LLM for its confidence (`tian2023justask`) | model self-opinion with no evidence behind it, and it puts an LLM in the decision path (ADR-001) |
| Train a learned aggregator to output probability | needs supervision we do not have, and destroys per-component transparency |
| Platt scaling / full isotonic as default | isotonic needs more held-out data than we have; it stays available as an option |
| Skip calibration, report accuracy only | leaves the confidence number meaningless while still displaying it, which is worse than not displaying it |
