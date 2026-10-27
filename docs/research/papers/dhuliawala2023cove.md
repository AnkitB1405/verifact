# dhuliawala2023cove

| Field | Value |
|---|---|
| **Title** | Chain-of-Verification Reduces Hallucination in Large Language Models |
| **Authors** | Dhuliawala, Komeili, Xu, Raileanu, Li, Celikyilmaz, Weston (7 authors) |
| **Identifier** | arXiv:2309.11495v2 |
| **Venue** | arXiv preprint (published venue not API-verified) |
| **Cluster** | C2 — self-verification prompting |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

A four-step prompting pipeline inside one model: (i) draft a response, (ii) plan verification questions about that draft, (iii) answer each question *independently* so the answers are not conditioned on the draft, (iv) regenerate a final response using the answers. Step (iii)'s independence is the key trick — it prevents the model from simply restating its own error.

## Inputs / outputs

**In:** a prompt. **Out:** a revised response, plus the intermediate verification Q&A.

## Strengths

- Reduces hallucination across list questions, closed-book QA and long-form generation with no retraining.
- The independence idea is a reusable principle, not just a prompt.
- Produces an intermediate artifact (the Q&A) that is partially interpretable.

## Limitations

- Entirely parametric: the verifier is the same model that made the error, so shared misconceptions survive.
- No external evidence, therefore no citation and no auditable provenance.
- Multiple LLM calls per response; cost grows with the number of verification questions. *(verify on full read)*

## Compute cost

≥ 2 + n LLM calls per response, n = number of verification questions.

## Reusable for VeriFact

The independence principle is adopted in our **correction self-check**: a generated correction is re-verified against retrieved evidence by the ordinary pipeline, not by asking the generator whether it is happy with its own output.

## Threat to our novelty

Low. No external evidence means no provenance, which is the property our brief requires.
