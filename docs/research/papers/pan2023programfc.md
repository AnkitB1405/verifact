# pan2023programfc

| Field | Value |
|---|---|
| **Title** | Fact-Checking Complex Claims with Program-Guided Reasoning |
| **Authors** | Pan, Wu, Nakov, Kan, Wang, Min + others (7 authors) |
| **Identifier** | arXiv:2305.12744v1 |
| **Venue** | arXiv preprint (ACL 2023 version widely cited; not API-verified here) |
| **Cluster** | C4 — multi-step reasoning for verification |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Decomposes a complex claim into simpler sub-tasks by having an LLM generate a **reasoning program** in-context; each sub-task is then delegated to a specialised handler (retrieval, QA, logical operation) from a shared library. The executed program is itself the explanation.

## Inputs / outputs

**In:** a complex claim. **Out:** a verdict plus an explicit program trace.

## Strengths

- **Explanation as a by-product of execution rather than a post-hoc narration** — the single most useful idea here, and it is what our component-score trace aims at by simpler means.
- Outperforms seven baselines across different settings of evidence availability, including sparse-evidence settings.
- Data-efficient: in-context, minimal training data.

## Limitations

- The program generator is an LLM, so the reasoning plan itself can be wrong, and a wrong plan produces a confidently wrong trace.
- Needs a curated function library; adding a new reasoning type means engineering.
- Programs are brittle for claims that are not cleanly decomposable. *(verify on full read)*
- Still a single aggregated verdict with no source-reliability or recency reasoning.

## Compute cost

LLM program generation + one or more handler calls per sub-task.

## Reusable for VeriFact

Cited as the alternative explainability strategy we **rejected**: we chose a fixed pipeline with preserved component scores over generated programs, because a fixed pipeline is reproducible, cheap, and auditable without trusting an LLM's reasoning plan. That trade-off goes in the architecture document as a documented rejection.

## Threat to our novelty

Moderate on explainability. Our counter-position is not that we explain better, but that we explain **deterministically and without an LLM in the decision path** — a different and defensible choice.
