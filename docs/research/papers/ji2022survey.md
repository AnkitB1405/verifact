# ji2022survey

| Field | Value |
|---|---|
| **Title** | Survey of Hallucination in Natural Language Generation |
| **Authors** | Ji, Lee, Frieske, Yu, Su, Xu, Ishii, Bang, Madotto, Fung + others (13 authors) |
| **Identifier** | arXiv:2202.03629v7 |
| **Venue** | ACM Computing Surveys (2022), doi:10.1145/3571730 — **venue and DOI API-verified** |
| **Cluster** | C1 — taxonomy and definitions |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

A broad survey of hallucination across NLG. Separates *intrinsic* hallucination (output contradicts the provided source) from *extrinsic* hallucination (output cannot be verified from the source — neither supported nor contradicted), reviews metrics and mitigation methods, then goes task by task (summarisation, dialogue, generative QA, data-to-text, MT, vision-language) before a section on LLMs.

## Inputs / outputs

N/A — survey.

## Strengths

- The intrinsic/extrinsic split is exactly the distinction our status set has to encode, and it comes from a peer-reviewed venue we can cite with a DOI.
- Comprehensive metric and mitigation inventory, useful for our related-work chapter.

## Limitations

- A survey, so no system to compare against.
- Pre-dates much of the LLM-era work; the LLM section is the thinnest part. *(verify on full read)*
- Task-specific framing (source-grounded NLG) does not map perfectly onto open-domain verification where there is no single given source.

## Compute cost

N/A.

## Reusable for VeriFact

**The definitional backbone of our report.** Extrinsic hallucination is precisely why `UNVERIFIABLE` must exist as a status separate from `CONTRADICTED`: unverifiable is the extrinsic case, contradicted is the intrinsic case against retrieved evidence.

## Threat to our novelty

None.
