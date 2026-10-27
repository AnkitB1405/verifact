# gao2023rarr

| Field | Value |
|---|---|
| **Title** | RARR: Researching and Revising What Language Models Say, Using Language Models |
| **Authors** | Gao, Dai, Pasupat, Chen, Chaganty, Fan, Zhao, Lao, Lee, Juan, Guu (11 authors) |
| **Identifier** | arXiv:2210.08726v3 |
| **Venue** | arXiv preprint (ACL 2023 version widely cited; not API-verified here) |
| **Cluster** | C4 / C7 — attribution and post-hoc revision |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Post-hoc, model-agnostic: given any generated text, RARR (i) researches attribution by generating queries, searching, and checking agreement, then (ii) **post-edits** the output to fix unsupported content while changing as little as possible. Requires only a handful of training examples, an LLM, and standard web search.

## Inputs / outputs

**In:** generated text. **Out:** revised text + attributions.

## Strengths

- **The closest existing system to our mitigation module**, and the source of the preservation principle: edit minimally, keep the original meaning.
- Model-agnostic and post-hoc, exactly our integration posture.
- Reports improved attribution with much better preservation of the original than earlier edit models.

## Limitations

- **Uses standard web search**, so evidence is whatever the engine returns, with no source-reliability policy. Our brief forbids this.
- The reviser is an LLM, which can introduce new unsupported content while fixing old content.
- **No abstention discussed** — the framing is revise, not decline. A system that always revises will sometimes revise a correct claim into an incorrect one.
- No calibrated confidence attached to the revision.
- Multiple LLM calls per sentence. *(verify on full read)*

## Compute cost

Query generation + web search + agreement check + edit, all LLM-mediated, per claim.

## Reusable for VeriFact

**The direct baseline and comparison point for our correction module**, and the explicit contrast for three of our requirements: a closed source registry, abstention, and a correction confidence bounded by its evidence.

## Threat to our novelty

**Highest of any paper surveyed for the mitigation half of the project.** Our defensible differences are: restricted and reliability-tiered sources instead of open web search; explicit abstention; correction confidence capped by evidence confidence; and a correction that is re-verified by the same pipeline before being shown. These must be stated as differences from RARR, not as inventions.
