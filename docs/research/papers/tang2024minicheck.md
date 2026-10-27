# tang2024minicheck

| Field | Value |
|---|---|
| **Title** | MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents |
| **Authors** | Tang, Laban, Durrett (3 authors) |
| **Identifier** | arXiv:2404.10774v2 |
| **Venue** | arXiv preprint (EMNLP 2024 version widely cited; not API-verified here) |
| **Cluster** | C3 / C5 — efficient grounded verification |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Observes that checking each piece of a generation with an LLM call is very expensive. Builds small fact-checking models by synthesising training data with GPT-4 — deliberately constructing realistic factual errors through a structured generation procedure — so the student model learns to check each fact in a claim and to recognise information synthesised across sentences. Also unifies prior fact-checking datasets into a benchmark (LLM-AggreFact).

## Inputs / outputs

**In:** a claim + a grounding document. **Out:** a supported / not-supported judgement.

## Strengths

- Reports GPT-4-level grounding accuracy at a stated 400× lower cost, with a 770M-parameter best system — strong evidence that a small local model is a legitimate choice for our NLI stage.
- Explicitly handles multi-sentence synthesis, which a sentence-pair NLI model does not.
- Releases models and benchmark.

## Limitations

- Binary grounded/not-grounded against a **given** document — it does not retrieve, does not handle source disagreement, and has no contradicted-vs-unverifiable distinction.
- Trained on GPT-4-synthesised errors, so it inherits that model's notion of what a plausible error looks like. *(verify on full read)*
- Still a learned black box: it gives a label, not a decomposed explanation.

## Compute cost

A 770M model at inference — far cheaper than an LLM call, more expensive than a 180M cross-encoder.

## Reusable for VeriFact

Cited as justification for **escalating to a slightly larger local checker rather than to an API LLM** in our adaptive-budget policy. A candidate backend for the NLI stage if DeBERTa-small underperforms.

## Threat to our novelty

Moderate on the per-claim checking stage. It does not retrieve, weight sources, calibrate, abstain or correct, so it is a component we could consume, not a competitor system.
