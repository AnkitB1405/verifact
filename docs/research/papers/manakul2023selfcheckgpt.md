# manakul2023selfcheckgpt

| Field | Value |
|---|---|
| **Title** | SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models |
| **Authors** | Manakul, Liusie, Gales (3 authors) |
| **Identifier** | arXiv:2303.08896v3 |
| **Venue** | arXiv preprint (published venue not API-verified — confirm before citing) |
| **Cluster** | C2 — self-consistency / sampling detection |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Samples several responses from the same LLM for the same prompt and measures how much they agree. The premise is that if the model actually holds a fact, independently sampled responses stay consistent; a hallucinated fact diverges and the samples contradict each other. No external database and no access to output logits is required, which is why it is called zero-resource and black-box. Consistency is measured between the sentence under test and the sampled passages by several variants (the paper reports BERTScore-, QA- and n-gram-based scoring).

## Inputs / outputs

**In:** one target passage + k resampled passages from the same model. **Out:** a per-sentence inconsistency score, and a passage-level factuality ranking.

## Strengths

- Needs no retrieval corpus and no logits, so it works against a closed commercial API.
- Operates at sentence granularity, which matches our claim-level reporting.
- Reported considerably higher AUC-PR than grey-box (logit-based) methods on their WikiBio-based annotation set.

## Limitations

- **Measures self-consistency, not truth.** A model that is confidently and consistently wrong scores as factual. This is the decisive limitation for us. *(verify on full read)*
- Cost scales linearly with k samples of a full generation — expensive per passage.
- Requires the ability to resample the *original* generator, which a verification service sitting downstream of arbitrary text does not have.
- Gives no evidence and no citation, so it cannot explain or correct anything.

## Compute cost

k full LLM generations per passage checked (the paper's setup uses GPT-3 samples), plus the chosen consistency scorer. No retrieval index.

## Reusable for VeriFact

Potentially as **Baseline 0** (a no-retrieval detector) to show what evidence buys us. We do not adopt it in the pipeline, because VeriFact receives text from an arbitrary upstream model and often cannot resample it.

## Threat to our novelty

Low. It solves a different problem (detection without evidence) and explicitly cannot produce evidence, citations, or corrections — all of which are core VeriFact requirements.
