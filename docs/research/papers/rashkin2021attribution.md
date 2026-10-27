# rashkin2021attribution

| Field | Value |
|---|---|
| **Title** | Measuring Attribution in Natural Language Generation Models |
| **Authors** | Rashkin, Nikolaev, Lamm, Aroyo, Collins, Das, Petrov, Tomar, Turc, Reitter (10 authors) |
| **Identifier** | arXiv:2112.12870v2 |
| **Venue** | arXiv preprint (TACL version widely cited; not API-verified here) |
| **Cluster** | C3 — attribution framework |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Defines **Attributable to Identified Sources (AIS)**: a formal framework for asking whether a generated statement is supported by an identified source. Introduces a two-stage human annotation pipeline — first decide whether the statement is interpretable on its own, then decide whether it is attributable to the source — and validates it across conversational QA, summarisation and table-to-text.

## Inputs / outputs

**In:** a generated statement + a cited source. **Out:** interpretable? and attributable?

## Strengths

- **The two-stage structure is an important design lesson**: a statement must be *interpretable standalone* before attribution can even be judged. That is exactly why our decomposition must resolve context before verification, and why vague or context-dependent claims belong in `AMBIGUOUS` rather than being forced to a verdict.
- Gives us precise vocabulary (attribution, not truth) for what the system actually measures — important for the viva.

## Limitations

- A human annotation framework, not an automatic method.
- Assumes the source is already identified; retrieval is out of scope. *(verify on full read)*

## Compute cost

N/A — human annotation.

## Reusable for VeriFact

**The conceptual basis of our `AMBIGUOUS` status and of our abstention rule.** Also the source of the careful wording throughout our documentation: VeriFact measures attribution to trusted sources, not truth.

## Threat to our novelty

None — it is a measurement framework we adopt the vocabulary of.
