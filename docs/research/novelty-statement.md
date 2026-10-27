# Novelty Statement

One page. Written after the gap matrix, and deliberately narrow.

## What is not novel

The pipeline shape — decompose → retrieve → infer → aggregate → explain → correct — is the
standard automated fact-checking pipeline described by Guo, Schlichtkrull and Vlachos
(arXiv:2108.11896). Claim decomposition is FActScore's. Retrieval-then-NLI is FEVER's.
Post-hoc correction is RARR's. Knowledge-graph verification is Shiralkar et al.'s.
**Assembling these is engineering, not research, and the report must say so in these words.**

## What we claim

> **Evidence-aware, calibrated, abstention-capable claim verification.**
>
> VeriFact weights each retrieved passage by its source's reliability tier and its age before
> aggregating entailment evidence; maps the aggregate onto six statuses that separate
> *contradicted* from *unverifiable*, *insufficient*, *outdated* and *ambiguous*; calibrates
> the reported confidence on a held-out split and reports Expected Calibration Error; and
> declines to correct a claim when the evidence will not support a correction.

Four testable sub-claims:

| # | Claim | How it is tested | How it is falsified |
|---|-------|------------------|---------------------|
| **H1a** | Reliability- and recency-weighted aggregation beats unweighted aggregation | Proposed vs Baseline C, and the −reliability ablation | No F1/AUROC gain outside run-to-run variance |
| **H1b** | Adding a KG consistency signal reduces false CONTRADICTED verdicts | −KG ablation, measured on the FP slice | FP rate unchanged or worse |
| **H1c** | Post-hoc calibration materially improves confidence reliability | ECE before vs after fitting, on test | ECE does not improve |
| **H2** | Uncertainty-driven escalation recovers most of the accuracy of always-max budget at much lower mean cost | cost/accuracy curve: adaptive vs fixed-low vs fixed-high | Adaptive sits on or below the line between the fixed policies |

## Secondary contribution, independent of whether H1/H2 hold

A **six-status verification scheme with an evaluation set that can actually exercise it.**
FEVER has three labels; FActScore, MiniCheck and HaluEval are binary. None of them can
distinguish *outdated* from *contradicted*, or *ambiguous* from *unverifiable*. The
hand-built `verifact-stress` set (120 items, 7 categories, two-person review, gold evidence
URLs, released under CC BY 4.0) exists to make those distinctions measurable. This
contribution survives a null result on H1 and H2.

## If the hypotheses fail

The reported contribution becomes: a reproducible, CPU-only, fully explainable verification
framework; the six-status scheme and its evaluation set; and **the negative finding that
source-reliability weighting and KG consistency do not improve claim-level verification in
this setting** — with the error analysis explaining why. This is written down now, before any
results exist, so the conclusion cannot be quietly reshaped to fit whatever the numbers say.

## What we will never claim

- That the system determines truth. It measures **attribution to trusted sources**
  (vocabulary from Rashkin et al., arXiv:2112.12870).
- That a confidence score is a probability that a statement is true.
- That absence of evidence indicates falsehood.
- Any number not produced by a committed run with a recorded config hash and seed.
