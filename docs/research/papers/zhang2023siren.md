# zhang2023siren

| Field | Value |
|---|---|
| **Title** | Siren's Song in the AI Ocean: A Survey on Hallucination in Large Language Models |
| **Authors** | Zhang, Li, Cui, Cai, Liu, Fu, Huang, Zhao, Zhang, Chen, Wang, Luu, Bi, Shi, Shi (16 authors) |
| **Identifier** | arXiv:2309.01219v3 |
| **Venue** | arXiv preprint (published venue not API-verified) |
| **Cluster** | C1 — taxonomy and definitions |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

LLM-specific hallucination survey. Taxonomises hallucination into input-conflicting, context-conflicting and fact-conflicting, and organises the literature into detection, explanation and mitigation. Reviews evaluation benchmarks.

## Inputs / outputs

N/A — survey.

## Strengths

- The three-way conflict taxonomy is cleaner than binary intrinsic/extrinsic for our purposes: VeriFact targets the *fact-conflicting* class specifically, and saying so sharpens our scope statement.
- Up-to-date benchmark inventory to cross-check our dataset choices.

## Limitations

- Preprint; no peer-reviewed venue confirmed by the API.
- Taxonomy is descriptive, not operational — it does not say how to decide a class automatically.
- Surveys move fast and this one is now dated relative to 2025-26 work. *(verify on full read)*

## Compute cost

N/A.

## Reusable for VeriFact

Used to **scope** the project in the SRS: VeriFact addresses fact-conflicting hallucination against external sources, and explicitly does not address context-conflicting (self-contradiction within a passage).

## Threat to our novelty

None.
