# cormack2009rrf

| Field | Value |
|---|---|
| **Title** | Reciprocal rank fusion outperforms condorcet and individual rank learning methods |
| **Authors** | Cormack, Clarke, Buettcher (3 authors) |
| **Identifier** | doi:10.1145/1571941.1572114 |
| **Venue** | Proceedings of the 32nd international ACM SIGIR conference, 2009 — **venue and DOI API-verified via Crossref** |
| **Cluster** | C4 — rank fusion |
| **Metadata** | verified via Crossref API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Combines several ranked result lists by summing, for each document, 1/(k + rank) over the lists that return it, with a small constant k damping the influence of top ranks. No training, no score normalisation, no tuning beyond k.

## Inputs / outputs

**In:** several ranked lists. **Out:** one fused ranking.

## Strengths

- **Needs no score normalisation**, which is the decisive practical property for us: BM25 scores and cosine similarities are not on a comparable scale and cannot simply be added.
- No training data, three lines of code, and reported to outperform Condorcet fusion and individual rank-learning methods.

## Limitations

- Uses only rank, so it discards the magnitude of agreement between retrievers.
- k is a free parameter (commonly 60) that we must set and justify rather than copy silently.
- A learned reranker will generally beat it given training data — which we do not have. *(verify on full read)*

## Compute cost

Negligible.

## Reusable for VeriFact

**Our retrieval fusion method.** It is also the honest answer to 'why not a learned reranker': no training data, no training budget, and a strong tuning-free baseline.

## Threat to our novelty

None.
