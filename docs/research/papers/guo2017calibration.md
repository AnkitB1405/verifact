# guo2017calibration

| Field | Value |
|---|---|
| **Title** | On Calibration of Modern Neural Networks |
| **Authors** | Guo, Pleiss, Sun, Weinberger (4 authors) |
| **Identifier** | arXiv:1706.04599v2 |
| **Venue** | arXiv preprint (ICML 2017 version widely cited; not API-verified here) |
| **Cluster** | C7 — calibration |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Shows that modern deep networks are **poorly calibrated** — their confidence does not match their accuracy — unlike shallower networks of a decade earlier, and identifies depth, width, weight decay and batch normalisation as contributing factors. Evaluates post-hoc calibration methods and finds **temperature scaling**, a single-parameter variant of Platt scaling, surprisingly effective on most datasets.

## Inputs / outputs

**In:** uncalibrated logits + a held-out set. **Out:** calibrated probabilities.

## Strengths

- **The citation that makes our calibration stage non-optional.** It establishes that a softmax output is not a probability, which is the single most defensible methodological point in our project.
- Temperature scaling is one parameter fitted on a dev set — essentially free to implement and to explain.
- Gives us Expected Calibration Error as the metric to report.

## Limitations

- Vision/document classification, not NLI over retrieved evidence; transfer is an assumption we must state. *(verify on full read)*
- Temperature scaling fixes average confidence, not per-group miscalibration: it can leave a specific slice (say, numeric claims) badly calibrated while the overall ECE looks fine.
- Needs a held-out set of adequate size — a real constraint given our small hand-built dataset.

## Compute cost

Negligible — fitting one scalar.

## Reusable for VeriFact

**The basis of verification stage S5's calibration step and of the `calibrated` flag on every `Verdict`.** We implement temperature scaling as the default and isotonic regression as the configurable alternative, and report ECE before and after.

## Threat to our novelty

None — a method we adopt and cite.
