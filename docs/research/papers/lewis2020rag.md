# lewis2020rag

| Field | Value |
|---|---|
| **Title** | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks |
| **Authors** | Lewis, Perez, Piktus, Petroni, Karpukhin, Goyal, Küttler, Lewis, Yih, Rocktäschel, Riedel, Kiela (12 authors) |
| **Identifier** | arXiv:2005.11401v4 |
| **Venue** | arXiv preprint (NeurIPS 2020 version widely cited; not API-verified here) |
| **Cluster** | C4 — retrieval augmentation |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Combines a parametric seq2seq generator with non-parametric memory — a dense vector index over Wikipedia accessed by a pretrained neural retriever — and fine-tunes the pair end to end. Two formulations: one set of retrieved passages for the whole output, or different passages per generated token.

## Inputs / outputs

**In:** a query. **Out:** a generation conditioned on retrieved passages.

## Strengths

- The foundational citation for why external non-parametric memory beats parametric recall for knowledge-intensive work, and for why world knowledge can be **updated by swapping the index** rather than retraining.
- Reports more specific, diverse and factual generation than a parametric-only baseline.

## Limitations

- **RAG reduces hallucination, it does not detect or measure it.** There is no verdict, no confidence and no abstention — a RAG system still answers when retrieval fails.
- Retrieval quality is an unexamined upper bound on everything downstream.
- Treats all retrieved passages as equally trustworthy — no source reliability at all. *(verify on full read)*

## Compute cost

A dense index over Wikipedia plus generator fine-tuning — far beyond our budget, and we do not need it.

## Reusable for VeriFact

Motivational citation for the retrieval stage, and the clearest statement of the **gap we are addressing**: RAG grounds generation, VeriFact audits it.

## Threat to our novelty

None. Different task.
