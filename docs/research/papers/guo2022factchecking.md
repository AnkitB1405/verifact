# guo2022factchecking

| Field | Value |
|---|---|
| **Title** | A Survey on Automated Fact-Checking |
| **Authors** | Guo, Schlichtkrull, Vlachos (3 authors) |
| **Identifier** | arXiv:2108.11896v3 |
| **Venue** | arXiv preprint (TACL version widely cited; not API-verified here) |
| **Cluster** | C4 — fact-checking pipelines |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Surveys automated fact-checking as a pipeline: claim detection → evidence retrieval → verdict prediction → justification production. Unifies the inconsistent task definitions and label sets used across datasets, and inventories datasets and models.

## Inputs / outputs

N/A — survey.

## Strengths

- **The pipeline decomposition our architecture follows**, so we can cite a survey rather than claim the structure as our own invention.
- Explicitly names *justification production* as a pipeline stage, which supports treating explainability as a first-class component rather than a UI nicety.
- Documents that label sets differ across datasets — directly relevant to our six-status mapping problem.

## Limitations

- Survey, no system.
- Journalistic fact-checking framing: claims are human-authored and often politically contested, whereas ours are machine-generated and mostly encyclopaedic. *(verify on full read)*
- Pre-LLM in emphasis.

## Compute cost

N/A.

## Reusable for VeriFact

Cited as the source of the four-stage pipeline and as the justification for our label-mapping table (FEVER's SUPPORTED/REFUTED/NEI → our six statuses).

## Threat to our novelty

**Moderate, and it must be handled honestly.** This survey establishes that claim→retrieve→verify→justify is standard. Therefore assembling that pipeline is *not* our contribution, and the report must not imply otherwise. Our contribution must live in the weighting/calibration/abstention layer.
