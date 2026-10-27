# robertson2009bm25

| Field | Value |
|---|---|
| **Title** | The Probabilistic Relevance Framework: BM25 and Beyond |
| **Authors** | Robertson, Zaragoza (2 authors) |
| **Identifier** | doi:10.1561/1500000019 |
| **Venue** | Foundations and Trends in Information Retrieval, 2009 — **venue and DOI API-verified via Crossref** |
| **Cluster** | C4 — lexical retrieval |
| **Metadata** | verified via Crossref API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

The monograph treatment of the probabilistic relevance framework, deriving BM25 as a term-weighting and document-scoring function with term-frequency saturation (k1) and document-length normalisation (b), and situating it among related models and extensions.

## Inputs / outputs

**In:** a query + a document collection. **Out:** a relevance ranking.

## Strengths

- **Exact lexical matching**, which is where dense retrieval is weakest: rare named entities, numbers, dates, and identifiers that an embedding model has never seen.
- No training, fully interpretable scores, decades of validation.
- k1 and b are few and well understood, so our parameter choices are defensible instead of arbitrary.

## Limitations

- No semantics whatsoever: a paraphrase with no shared terms scores zero. This is the complementary failure to SBERT's, and is why our retriever runs both.
- Needs tokenisation and stemming decisions that materially affect results and must be documented. *(verify on full read)*
- Scores are not comparable across queries, which is why fusion must be rank-based.

## Compute cost

Linear in corpus size per query with `rank_bm25` — acceptable for our corpus, and the documented reason we did not deploy Elasticsearch.

## Reusable for VeriFact

**The lexical half of our hybrid retriever**, and the citation behind the claim that BM25 and dense retrieval fail in complementary ways.

## Threat to our novelty

None.
