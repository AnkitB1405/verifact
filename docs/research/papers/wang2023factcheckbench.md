# wang2023factcheckbench

| Field | Value |
|---|---|
| **Title** | Factcheck-Bench: Fine-Grained Evaluation Benchmark for Automatic Fact-checkers |
| **Authors** | Wang, Reddy, Mujahid, Arslan, Rauber, Mubarak, Nakov + others (13 authors) |
| **Identifier** | arXiv:2311.09000v3 |
| **Venue** | arXiv preprint (published venue not API-verified) |
| **Cluster** | C3 — evaluation of fact-checkers |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

An end-to-end annotation framework for the factuality of LLM responses, with a multi-stage scheme producing labels about **verifiability** as well as factual inconsistency. Builds an open-domain benchmark at three granularities — claim, sentence, document.

## Inputs / outputs

**In:** LLM responses. **Out:** multi-granularity factuality annotations.

## Strengths

- **Treats verifiability as its own annotation dimension**, which is direct external support for our `UNVERIFIABLE` status rather than forcing every claim into true/false.
- Three granularities match our claim→sentence→document traceability requirement.
- Reports that FacTool, FactScore and Perplexity.ai all struggle to identify false claims (best F1 = 0.63 in their setting) — a sober, citable statement of how hard this task is, useful for setting examiner expectations.

## Limitations

- A benchmark, not a system.
- Their best pipeline leans on GPT-4, so the reported ceiling may not transfer to a local-model system like ours. *(verify on full read)*
- Licensing and size need checking before we adopt it as a test set.

## Compute cost

N/A.

## Reusable for VeriFact

**Primary citation for why `UNVERIFIABLE` exists**, and a realistic reference point (F1 ≈ 0.6 range) so our own numbers are read in context instead of against an imagined 0.95.

## Threat to our novelty

None — it measures systems, it is not one.
