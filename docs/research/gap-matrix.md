# Gap Matrix

Surveyed systems × capability. Built from the 30 records in `papers/`.
Legend: **✓** present and central · **~** partial or implicit · **✗** absent.

Honesty note: every ✗ means *the paper does not address this*, not *the paper is bad*. Most
of these systems were not trying to do the thing the column names.

| System | 1 Claim decomp. | 2 Retrieval | 3 NLI / entail. | 4 KG check | 5 Source reliability | 6 Calibration | 7 Abstention | 8 Correction | 9 Per-component explanation | 10 Adaptive compute |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| SelfCheckGPT (2303.08896) | ~ sentence | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Semantic Uncertainty (2302.09664) | ✗ | ✗ | ~ clustering | ✗ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ |
| CoVe (2309.11495) | ~ questions | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ~ Q&A trace | ✗ |
| FActScore (2305.14251) | **✓** | ✓ | ~ LM judge | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| MiniCheck (2404.10774) | ~ | ✗ given doc | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| RARR (2210.08726) | ~ queries | ✓ web | ~ agreement | ✗ | ✗ | ✗ | ✗ | **✓** | ~ | ✗ |
| ALCE systems (2305.14627) | ✗ | ✓ fixed corpus | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ~ citations | ✗ |
| ProgramFC (2305.12744) | **✓** program | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** trace | ~ by program |
| FEVER pipeline (1803.05355) | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ~ NEI label | ✗ | ~ evidence set | ✗ |
| FEVEROUS (2106.05707) | ✗ | ✓ | ✓ | ~ tables | ✗ | ✗ | ~ NEI label | ✗ | ~ | ✗ |
| KGAT (1910.09796) | ✗ | ✓ | ✓ | ✗ evidence graph | ✗ | ✗ | ✗ | ✗ | ~ attention | ✗ |
| GEAR (1908.01843) | ✗ | ✓ | ✓ | ✗ evidence graph | ✗ | ✗ | ✗ | ✗ | ~ | ✗ |
| Knowledge Streams (1708.07239) | ✗ needs triple | ✗ | ✗ | **✓** | ✗ | ✗ | ✗ | ✗ | **✓** paths | ✗ |
| Neural Path Hunter (2104.08455) | ✗ | ~ k-hop | ~ critic | **✓** | ✗ | ✗ | ✗ | **✓** entities | ~ | ✗ |
| RAG (2005.11401) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | n/a generates | ✗ | ✗ |
| Temperature scaling (1706.04599) | — | — | — | — | — | **✓** | — | — | — | — |
| **VeriFact (proposed)** | ✓ | ✓ closed registry | ✓ | ✓ | **✓** | **✓** | **✓** | ✓ | **✓** scores | **✓** |

## What the matrix shows

**Columns that are well covered — we claim no novelty in these:**

- **1 Claim decomposition** — FActScore and ProgramFC own this. Our rules-first decomposer is
  a reproducibility choice, not a research contribution.
- **2 Retrieval** — standard since FEVER and RAG.
- **3 NLI / entailment** — standard since FEVER; MiniCheck is the efficient modern form.
- **8 Correction** — RARR, CoVe and Neural Path Hunter all post-edit. Correcting text is not new.
- **4 KG check** — Knowledge Streams and Neural Path Hunter both do real KG verification.

**Columns that are essentially empty across every surveyed system:**

- **5 Source reliability weighting — empty.** Every system treats its evidence pool as
  uniformly trustworthy. FEVER/FEVEROUS/FActScore use Wikipedia alone; RARR uses whatever a
  web search returns. None weights a passage by the reliability or the age of its source.
- **6 Calibration — empty in the fact-checking literature.** Guo et al. established that
  neural confidences are not probabilities, and Tian et al. studied LLM self-reported
  confidence, but none of the verification systems surveyed calibrates its verdict confidence
  or reports ECE. They report accuracy and F1 on a verdict, not reliability of a confidence.
- **7 Abstention — empty.** FEVER's NEI is a *label the system predicts*, not a decision to
  decline; RARR always revises. No surveyed system declines to act when its evidence is weak.
- **10 Adaptive compute — empty.** Every system spends the same budget on every claim.
  ProgramFC varies work by program shape, but not by uncertainty.
- **9 Per-component explanation — thin.** ProgramFC and Knowledge Streams are genuinely
  explainable; the rest offer attention weights or a citation list. None exposes a decomposed
  score per verification signal.

## The gap, stated precisely

> Existing systems verify claims against evidence they treat as uniformly reliable, emit an
> uncalibrated verdict, and always act. **The combination of (5) reliability- and
> recency-weighted evidence, (6) a calibrated confidence, (7) an explicit abstention
> decision, and (10) uncertainty-driven compute allocation, reported through (9) per-signal
> component scores, is not covered by any surveyed system.**

## Threats to this claim, recorded now rather than discovered at the viva

1. **Combination, not invention.** Each of columns 5–7 and 10 exists somewhere in the wider
   ML literature (source credibility in misinformation detection; calibration in
   classification; selective prediction / reject option; cascaded inference). Our claim must
   be scoped to *evidence-based claim verification*, and must say "not applied in this
   setting" rather than "new".
2. **Coverage of our survey.** 30 papers is not the field. Specifically unexamined:
   credibility-aware misinformation detection, selective-prediction literature, and
   2025–2026 work. Three of the four empty columns are the kind of thing a recent paper
   could already have closed. **Before the report is finalised, the team must run targeted
   searches on "source credibility fact verification", "selective prediction NLP" and
   "calibrated claim verification" and add what they find, even if it weakens the claim.**
3. **The gap may be empty for a reason.** Possibly nobody weights sources because it does not
   help. That is what H1's experiment is for, and a null result is a publishable outcome for
   a student project as long as it is reported as one.
