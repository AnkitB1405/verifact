# aly2021feverous

| Field | Value |
|---|---|
| **Title** | FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information |
| **Authors** | Aly, Guo, Schlichtkrull, Thorne, Vlachos, Christodoulopoulos, Cocarascu, Mittal (8 authors) |
| **Identifier** | arXiv:2106.05707v3 |
| **Venue** | arXiv preprint (NeurIPS 2021 Datasets track version widely cited; not API-verified) |
| **Cluster** | C4 / C6 — structured + unstructured evidence |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

87,026 verified claims where evidence may be Wikipedia **sentences and/or table cells**, labelled supports / refutes / not enough info. Documents deliberate effort to track and reduce dataset bias that would let a model predict the label without looking at evidence. Provides a baseline over text and tables.

## Inputs / outputs

**In:** a claim. **Out:** label + evidence as sentences and/or table cells.

## Strengths

- **Establishes that structured evidence matters alongside text** — the premise of our knowledge-graph stage, citable rather than asserted.
- Explicit bias-mitigation discussion, a good model for our own dataset construction.
- Their baseline predicts both correct evidence and verdict for only 18% of claims, which honestly frames the difficulty.

## Limitations

- Tables, not a knowledge graph: no entity identity, no relation semantics, no multi-hop paths.
- Still single-source (Wikipedia) and still has no recency dimension.
- Large and complex; full adoption is beyond our timeline. *(verify on full read)*

## Compute cost

Dataset; table-aware retrieval is heavier than sentence retrieval.

## Reusable for VeriFact

Cited as the justification for mixing structured and unstructured evidence. **Not used as a test set** — out of scope for our timeline, and we say so in Known Limitations rather than pretending otherwise.

## Threat to our novelty

Low. Structured evidence as tables is a different mechanism from entity-relation graph checking.
