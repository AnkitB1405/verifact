# Explainer Log — P4 — Verification, Scoring & Research Engineer

One entry per merged story. Three things: **what it does**, **why it exists**,
**what could go wrong**. This is the artifact behind the Definition of Done item
"the owner can explain it out loud".

Written from the commits actually merged, not from the plan. If an entry cannot
be delivered verbally without opening the code, it is not finished.

Module-level detail lives in `docs/design/`; this log is the per-change record.


## 27 Oct — Literature survey, 30 records

- **What it does:** 30 paper records across 7 clusters, every identifier verified against the arXiv or Crossref API.
- **Why it exists:** No citation was written from memory. Each record states its summary source and carries `full_text_read_by: <<TBD>>`, because the summaries come from published abstracts and pretending otherwise would be the easiest lie in the project.
- **What could go wrong:** 30 papers is not the field. Three of the four 'empty' gap-matrix columns are the kind a recent paper could already have closed, which is why a targeted search is required before the report.

## 27 Oct — Gap matrix and novelty statement

- **What it does:** 16 systems × 10 capabilities; the claim narrowed to four falsifiable sub-hypotheses.
- **Why it exists:** It states plainly that the pipeline shape, decomposition, retrieval+NLI, correction and KG verification are all prior work. The claim is confined to reliability weighting, calibration, abstention and adaptive compute.
- **What could go wrong:** 'Combination, not invention' is recorded as threat 1 against our own claim. If H1 fails the honest outcome is the negative result, which is written down *before* any experiment ran so the conclusion cannot be reshaped later.

## 28 Oct — The six statuses

- **What it does:** Each defined by an evidence condition with a worked example, plus the lossy mapping to FEVER and HaluEval labels.
- **Why it exists:** The whole system hangs on UNVERIFIABLE being distinct from CONTRADICTED. The mapping table is where the collapse to FEVER's three labels is made explicit rather than fudged in a metric.
- **What could go wrong:** OUTDATED and AMBIGUOUS have no equivalent in any public dataset surveyed, so they can only be evaluated on a set we build ourselves.

## 29 Oct — ADR-005 calibration protocol

- **What it does:** Temperature scaling on dev, `calibrated` set only when an artifact loads, and a binding threshold-freeze protocol.
- **Why it exists:** Reporting a raw margin as 'the probability this claim is true' is both what the brief forbids and the most obvious attack on the project. The protocol also binds the baselines to the same tuning budget — tuning ours while leaving theirs untouched would be a rigged experiment.
- **What could go wrong:** Temperature scaling fixes *average* confidence; a specific slice such as numeric claims can stay badly calibrated while the global ECE looks fine.

## 01 Nov — Stages S1 and S2

- **What it does:** Similarity and 3-way NLI, with a dependency-free fallback for both.
- **Why it exists:** The label order is read from the model's own `id2label`. `nli-deberta-v3-small` orders them {0: contradiction, 1: entailment, 2: neutral} — neither alphabetical nor intuitive — and a wrong guess would invert every verdict while leaving all plumbing tests green.
- **What could go wrong:** EA-05: the model gives contradiction ≈1.0 for passages that are merely irrelevant. Asserted as a test so it is a measured fact rather than a caveat, and it is contained, not fixed.

## 01 Nov — Stage S4 weighting

- **What it does:** w = reliability × recency decay × relevance, with duplicates collapsed and agreement counted per source.
- **Why it exists:** This is where the novelty claim actually lives. An undated passage gets a factor of 1.0 and is recorded as undated — never assumed recent and never penalised, because sparse metadata is the source's bookkeeping, not evidence about the claim.
- **What could go wrong:** Half-lives are a modelling choice with no empirical basis yet. Per-source agreement counting is the fix for the `kuhn2023semantic` problem, but near-duplicate detection is token overlap and will miss a true paraphrase.

## 01 Nov — Stage S5 aggregation

- **What it does:** E, C, coverage, and the six-status decision rule.
- **Why it exists:** Two invariants have dedicated tests: no evidence gives UNVERIFIABLE, and a MISSING graph result is inert. `test_every_status_is_reachable` exists because a status that cannot be produced is dead documentation.
- **What could go wrong:** Every threshold is a placeholder and the freeze protocol has not run, so no reported number may depend on them yet.

## 02 Nov — Calibration and ECE

- **What it does:** Temperature fitted by grid search on ECE; measured 0.1619 → 0.0055 on a synthetic overconfident scorer.
- **Why it exists:** Grid search on ECE rather than NLL, so we minimise the metric we actually report instead of claiming an improvement on a different objective.
- **What could go wrong:** That number is synthetic. No ECE has been measured on real verification data, and the dev split from a 120-item set will be noisy.

## 02 Nov — Engine and explanation assembler

- **What it does:** Five stages wired, adaptive escalation, deterministic explanations.
- **Why it exists:** `budget_spent` on every verdict is what makes the H2 cost/accuracy curve measurable. Explanations are assembled from scores because a generated explanation of this system's output would be its one unverified claim.
- **What could go wrong:** Escalation triggers are hand-chosen, not learned. If H2 fails the honest outcome is to report that the policy bought nothing.

## 02 Nov — Two aggregation fixes

- **What it does:** Honoured KG support, gated on absolute similarity, and made confidence come from the deciding branch.
- **Why it exists:** The rule consulted the graph only for contradiction, so a tier-1 confirmation was overridable by text NLI — which returned CONTRADICTED for Marie Curie's 1903 prize while the graph confirmed it. And coverage could never report 'nothing relevant found' because relevance is min-max scaled per claim (EA-07).
- **What could go wrong:** EA-08 is left open on purpose: a fabricated entity still returns CONTRADICTED where UNVERIFIABLE would be honest. Closing it by raising a threshold would be fitting to one hand-picked example.

## 02 Nov — Negation scoping fix (EA-10)

- **What it does:** Polarity and numeric checks scoped to the premise sentence that overlaps the claim.
- **Why it exists:** Reported by P2's injection suite. A negation belongs to the sentence it occurs in; comparing across the whole passage made the fallback backend flippable by one appended sentence.
- **What could go wrong:** The fallback now under-detects contradictions from entity substitution, which is the safe direction and is stated wherever its numbers appear.
