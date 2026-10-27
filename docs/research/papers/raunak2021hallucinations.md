# raunak2021hallucinations

| Field | Value |
|---|---|
| **Title** | The Curious Case of Hallucinations in Neural Machine Translation |
| **Authors** | Raunak, Menezes, Junczys-Dowmunt (3 authors) |
| **Identifier** | arXiv:2104.06683v1 |
| **Venue** | arXiv preprint (NAACL 2021 version widely cited; not API-verified here) |
| **Cluster** | C1 — causes of hallucination |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Studies hallucination in NMT as an extreme failure mode. Connects hallucination under source perturbation to long-tail memorisation theory, and shows that two natural hallucination types (detached and oscillatory outputs) arise from identifiable corpus-level noise patterns. Also shows backtranslation and sequence-level distillation *amplify* hallucination.

## Inputs / outputs

N/A — analysis.

## Strengths

- One of the few papers that explains *why* hallucination happens rather than only measuring it, which strengthens our introduction.
- The data-amplification result is a useful caution about synthetic training data.

## Limitations

- MT-specific; transfer to open-ended LLM generation is an assumption, not a result. *(verify on full read)*
- Offers no detection method we can use.

## Compute cost

N/A.

## Reusable for VeriFact

Introduction/motivation only — the causal account of hallucination. Not used in the pipeline.

## Threat to our novelty

None.
