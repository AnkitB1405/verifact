# liu2020kgat

| Field | Value |
|---|---|
| **Title** | Fine-grained Fact Verification with Kernel Graph Attention Network |
| **Authors** | Liu, Xiong, Sun, Liu (4 authors) |
| **Identifier** | arXiv:1910.09796v4 |
| **Venue** | arXiv preprint (ACL 2020 version widely cited; not API-verified here) |
| **Cluster** | C6 — graph-based evidence reasoning |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Builds an **evidence graph** whose nodes are candidate evidence sentences for a claim, then applies kernel-based attention: node kernels weigh how important each evidence node is, edge kernels propagate information between evidence nodes at a finer granularity than dot-product attention. Reports a 70.38% FEVER score, and shows the kernel attention concentrates on the genuinely relevant evidence.

## Inputs / outputs

**In:** a claim + candidate evidence sentences. **Out:** a 3-way verdict, with attention weights over evidence.

## Strengths

- **Shows that *jointly* reasoning over multiple evidence pieces beats scoring each independently and taking a max** — a direct challenge to our simple weighted aggregation, and an honest one we must acknowledge.
- Attention weights give a form of evidence-level interpretability.
- Strong, reproducible FEVER number to reference.

## Limitations

- A graph over *evidence sentences*, **not** over entities and relations. It is not knowledge-graph verification in our sense, despite the name.
- Learned end-to-end on FEVER, so it needs training data and is tied to FEVER's label set and distribution.
- Attention weights are a weak form of explanation: they say where the model looked, not what rule decided the verdict. *(verify on full read)*
- No source reliability, recency or calibration.

## Compute cost

BERT encoding of every claim-evidence pair plus graph attention; training required.

## Reusable for VeriFact

Cited as the **main threat to our aggregation stage** and as a documented alternative. Our counter-argument must be stated carefully: we choose a transparent weighted aggregation with preserved component scores over a learned attention model, trading some accuracy for auditability and for not needing FEVER-specific training. Whether that trade is worth it is an empirical question for Phase 10.

## Threat to our novelty

**Moderate-to-high on evidence aggregation.** We must not claim that aggregating multiple evidence pieces is novel. Our claim is confined to *what goes into the weights* (source reliability, recency, KG consistency) and to calibrated, abstention-capable output.
