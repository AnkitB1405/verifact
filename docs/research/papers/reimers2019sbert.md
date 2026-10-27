# reimers2019sbert

| Field | Value |
|---|---|
| **Title** | Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks |
| **Authors** | Reimers, Gurevych (2 authors) |
| **Identifier** | arXiv:1908.10084v1 |
| **Venue** | arXiv preprint (EMNLP 2019 version widely cited; not API-verified here) |
| **Cluster** | C5 — the embedding backbone we use |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Cross-encoder BERT requires both sentences in one forward pass, so finding the most similar pair among 10,000 sentences takes ~65 hours. SBERT fine-tunes BERT with siamese and triplet structures so that each sentence can be encoded **once** into a fixed vector and compared by cosine similarity, cutting that to about 5 seconds while retaining accuracy.

## Inputs / outputs

**In:** a sentence. **Out:** a dense vector comparable by cosine similarity.

## Strengths

- **The reason our architecture can afford both dense retrieval and NLI**: embeddings are precomputed once per passage, and only the short-listed passages go through the expensive cross-encoder.
- Clean quantification of the bi-encoder vs cross-encoder trade-off — the core of our retrieve-then-rerank design, and an easy viva answer.

## Limitations

- Cosine similarity measures **topical relatedness, not entailment**. 'Einstein was born in Ulm' and 'Einstein was not born in Ulm' are near-identical in embedding space. This is precisely why similarity cannot be the verification signal and is only stage S1.
- Quality depends on the fine-tuning data; small distilled variants trade accuracy for speed. *(verify on full read)*

## Compute cost

One forward pass per passage at index time; cosine comparison is trivial. `all-MiniLM-L6-v2` (384-d) is CPU-practical.

## Reusable for VeriFact

**Stage S1 and the dense half of retrieval.** Also the single clearest citation for the viva question 'why is semantic similarity insufficient?'

## Threat to our novelty

None — a component we consume.
