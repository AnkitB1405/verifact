# shiralkar2017streams

| Field | Value |
|---|---|
| **Title** | Finding Streams in Knowledge Graphs to Support Fact Checking |
| **Authors** | Shiralkar, Flammini, Menczer, Ciampaglia (4 authors) |
| **Identifier** | arXiv:1708.07239v1 |
| **Venue** | arXiv preprint (ICDM 2017 version widely cited; not API-verified here) |
| **Cluster** | C6 — knowledge-graph fact checking |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

**Genuine knowledge-graph verification.** Treats a claim as a (subject, predicate, object) triple and the background knowledge graph as a flow network, with knowledge as an abstract commodity. Checking the triple becomes finding a maximum 'knowledge stream' from subject to object through connecting paths. Unsupervised — no training data at all. Also surfaces interpretable path patterns for a human checker.

## Inputs / outputs

**In:** an (s, p, o) triple + a knowledge graph. **Out:** a truthfulness score plus the supporting paths.

## Strengths

- **Unsupervised and genuinely explainable**: the output is a path a human can read, which is what our KG stage needs to show in the dashboard.
- Reported to outperform existing algorithms on several hand-crafted and real-world fact sets across varied domains.
- Requires no labelled data, so it fits a project with no training budget.

## Limitations

- **Requires the claim to already be a clean triple.** Mapping arbitrary natural-language claims to triples is the hard part, and it is left outside the method — which is exactly where our P2/P3 boundary sits.
- Path existence conflates association with assertion: a dense path between two entities is not the same as the specific relation holding.
- **Cannot distinguish a missing relation from a false one** — the central failure we have to engineer around, since a sparse region of the graph produces a low score for a true fact.
- No temporal reasoning, so an outdated graph silently produces wrong verdicts. *(verify on full read)*

## Compute cost

Graph flow computation over a subgraph — cheap relative to transformer inference, and it is why NetworkX in-process is adequate for us.

## Reusable for VeriFact

**The direct ancestor of our KG consistency stage**, and the reason our `KGCheck` has a `MISSING` status distinct from `CONTRADICTED`: this paper's inability to make that distinction is the limitation we explicitly engineer against.

## Threat to our novelty

Moderate on the KG stage in isolation. Our difference is that the KG result is one weighted signal among several and can never alone produce a CONTRADICTED verdict, whereas here the path score *is* the verdict.
