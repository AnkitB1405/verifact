# zhou2019gear

| Field | Value |
|---|---|
| **Title** | GEAR: Graph-based Evidence Aggregating and Reasoning for Fact Verification |
| **Authors** | Zhou, Han, Hou, Liu, Li, Sun + others (7 authors) |
| **Identifier** | arXiv:1908.01843v1 |
| **Venue** | arXiv preprint (ACL 2019 version widely cited; not API-verified here) |
| **Cluster** | C6 — evidence aggregation |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Notes that earlier systems merely concatenated evidence, preventing evidence pieces from informing one another. Builds a fully-connected evidence graph, lets information transfer across it, and applies different aggregators to pool multi-evidence information, with BERT as the encoder. Reports a 67.10% FEVER test score.

## Inputs / outputs

**In:** claim + retrieved evidence set. **Out:** 3-way verdict.

## Strengths

- Clean statement of the problem with naive concatenation, which is a real failure mode in our own design if we are careless.
- Compares several aggregator choices, useful when we justify ours.

## Limitations

- Same core limitation as KGAT: a graph over evidence sentences, not over entities and relations.
- Needs supervised training on FEVER.
- Superseded by KGAT on the same benchmark. *(verify on full read)*

## Compute cost

BERT per claim-evidence pair plus graph layers; training required.

## Reusable for VeriFact

Historical context for the aggregation chapter, and the source of the explicit warning against simple concatenation of evidence into one premise.

## Threat to our novelty

Low — superseded, and again a different sense of graph.
