# kuhn2023semantic

| Field | Value |
|---|---|
| **Title** | Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation |
| **Authors** | Kuhn, Gal, Farquhar (3 authors) |
| **Identifier** | arXiv:2302.09664v3 |
| **Venue** | arXiv preprint (published venue not API-verified) |
| **Cluster** | C2 — uncertainty estimation |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Points out that token-level entropy over generations is the wrong uncertainty measure for language, because many different token sequences mean the same thing (semantic equivalence). Clusters sampled generations into meaning-equivalence classes and computes entropy *over the clusters* instead of over sequences. Unsupervised, single model, no modification to the model.

## Inputs / outputs

**In:** a question and k sampled answers. **Out:** a scalar semantic entropy, higher = more uncertain.

## Strengths

- Fixes a genuine conceptual error in naive entropy-based uncertainty.
- Reported more predictive of model accuracy on QA than comparable baselines.
- The *idea* transfers: equivalent evidence passages should not be counted as independent agreement.

## Limitations

- Again measures the generator's internal uncertainty, not external support.
- Needs k samples per item.
- Requires an equivalence-clustering step, itself usually an NLI model — so it inherits NLI errors. *(verify on full read)*

## Compute cost

k generations + pairwise equivalence checks per item (quadratic in k for the clustering step).

## Reusable for VeriFact

**Directly relevant to our cross-source agreement term.** Two paraphrased passages from mirrored sources must not be treated as two independent confirmations. We cite this as the justification for deduplicating near-identical evidence before computing agreement.

## Threat to our novelty

None — orthogonal. It informs one term in our weighting, it does not pre-empt the architecture.
