# Research Plan (Phase 1 execution plan)

This is a **plan**, not a literature review. No paper is summarised here from memory.
Every row in the survey table below must be filled only after the paper has actually been
read, and must carry a DOI/arXiv id. Fabricated citations are a project-failing defect.

## 1. Survey scope — six clusters

| Cluster | What we need out of it | Owner |
|---|---|---|
| C1 Hallucination taxonomy & definitions | A defensible definition of "hallucination" we use consistently | P4 |
| C2 Self-consistency / sampling detection (e.g. SelfCheckGPT family) | Whether a no-retrieval baseline is worth adding as Baseline 0 | P4 |
| C3 Decomposition & atomic-fact scoring (e.g. FActScore family) | Our claim-decomposition definition of "atomic" | P2 |
| C4 Retrieval-augmented fact verification (FEVER-line systems, RAG verification) | Retrieval metric choice (Recall@k), evidence granularity | P3 |
| C5 NLI for verification | Which checkpoint, label mapping, known failure modes | P4 |
| C6 KG / structured fact checking (Wikidata-based, path-based) | Which relations are checkable, how to handle KG incompleteness | P3 |

## 2. Per-paper record (mandatory template)

Each entry goes in `docs/research/papers/<key>.md`:

```
key:            <firstauthor><year><word>
title:
venue/year:
doi_or_arxiv:
read_by:        <team member>  date: <YYYY-MM-DD>
core method:    (3-5 sentences, mechanism not marketing)
inputs/outputs:
strengths:
limitations:    (at least two, specific)
compute cost:   (model size, #LLM calls per claim, reported latency if any)
reusable for us:(what exactly, or "nothing")
threat to novelty: (does this already do what we propose? honestly)
```

Minimum: **18 papers**, ≥3 per cluster. Target 24.

## 3. Research-gap protocol

We may only state a gap after producing `docs/research/gap-matrix.md`: a table of
surveyed systems × capability columns —

`claim decomposition | retrieval | NLI | KG check | source-reliability weighting | calibration | abstention | correction | per-component explanation | adaptive compute`

A gap is a column (or combination of columns) that is empty or weakly covered across the
surveyed rows. If the matrix shows our intended contribution is already covered, **we change
the contribution**, not the matrix.

## 4. Candidate contribution (hypothesis, to be falsified or confirmed)

> **H1 — Evidence-aware multi-stage verification.** Combining NLI with (a) explicit source-
> reliability and recency weighting and (b) a knowledge-graph consistency signal produces
> better-calibrated claim-level verdicts and fewer false "hallucination" flags than
> retrieval+NLI alone, at comparable latency.
>
> **H2 — Adaptive verification budget.** Spending extra retrieval/NLI budget only on claims
> that are uncertain or whose evidence conflicts recovers most of the accuracy of
> always-maximum budget at a fraction of the mean cost.

Both are **experimentally falsifiable** and both are tested in Phase 10:
- H1 → Proposed system vs Baseline C (retrieval+NLI). Metrics: F1, AUROC, ECE, FPR on the
  "true-but-unretrievable" slice of the test set.
- H2 → cost/accuracy curve: adaptive policy vs fixed-low vs fixed-high budget.

If H1 shows no improvement, the reported contribution becomes the **negative result plus the
explainability/abstention framework**, and we say so. That is an acceptable academic outcome.
Claiming an unmeasured improvement is not.

## 5. Baselines (frozen now, so they can't be tuned to lose)

| id | Description |
|----|-------------|
| A | Similarity-only: embed claim + top-k evidence, threshold on max cosine. |
| B | NLI-only: NLI against the *source text itself* (no retrieval). |
| C | Retrieval + NLI: top-k retrieval, max-entailment aggregation. |
| D | **Proposed**: C + source reliability/recency weighting + KG consistency + calibrated aggregation + abstention. |

Baseline hyperparameters are chosen on a **dev split** and frozen before touching test.

## 6. Datasets — licence check before download

| Dataset | Use | Licence to verify | Status |
|---|---|---|---|
| FEVER | claim-level verification, Recall@k | CC BY-SA 3.0 (verify) | `<<TBD: verified?>>` |
| HaluEval | hallucination detection | verify repo licence | `<<TBD>>` |
| TruthfulQA | qualitative stress set | Apache-2.0 (verify) | `<<TBD>>` |
| Hand-built `verifact-stress` (~120 claims) | the 7 required categories, incl. outdated & ambiguous | ours, CC BY 4.0 | to build in Sprint 5 |

`verifact-stress` is built by the team because no public set cleanly covers *outdated* and
*insufficient-evidence* cases. Each item: claim, gold status, gold evidence URL, who wrote it,
who reviewed it. Two-person review required — the author never labels their own item.

## 7. Phase 1 timebox

5 working days. Deliverables: 18+ paper records, `gap-matrix.md`, a 1-page
`novelty-statement.md`, and a GO/CHANGE decision on H1/H2 recorded in
`docs/research/decisions/ADR-001-contribution.md`.
