# lin2022truthfulqa

| Field | Value |
|---|---|
| **Title** | TruthfulQA: Measuring How Models Mimic Human Falsehoods |
| **Authors** | Lin, Hilton, Evans (3 authors) |
| **Identifier** | arXiv:2109.07958v2 |
| **Venue** | arXiv preprint (ACL 2022 version widely cited; not API-verified here) |
| **Cluster** | C1 / evaluation |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

817 questions over 38 categories (health, law, finance, politics and others), deliberately written so that a human might answer falsely from a common misconception. A model does well only by avoiding false answers it would have learned by imitating human text. Best model tested was truthful on 58% of questions against 94% for humans; notably, **larger models were generally less truthful**.

## Inputs / outputs

**In:** a question. **Out:** an answer judged truthful or not.

## Strengths

- The inverse-scaling result is a powerful motivating fact for the introduction: this problem does not go away with bigger models.
- Adversarially constructed around misconceptions, so it stresses exactly the case where retrieval must override the model's prior.

## Limitations

- **Question-answering, not claim verification.** Items are not claims with gold evidence, so it cannot be used for our main P/R/F1 tables without re-annotation.
- Small (817 items) and partly about contested or normative statements where 'truthful' is itself debatable. *(verify on full read)*
- Known to be sensitive to the judging method.

## Compute cost

N/A.

## Reusable for VeriFact

**Qualitative stress set only**, and a motivating citation. Using it as a primary quantitative benchmark would be a category error, and the test report must say so explicitly rather than quietly reporting a number on it.

## Threat to our novelty

None.
