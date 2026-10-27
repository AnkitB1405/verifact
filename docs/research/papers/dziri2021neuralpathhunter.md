# dziri2021neuralpathhunter

| Field | Value |
|---|---|
| **Title** | Neural Path Hunter: Reducing Hallucination in Dialogue Systems via Path Grounding |
| **Authors** | Dziri, Madotto, Zaïane, Bose (4 authors) |
| **Identifier** | arXiv:2104.08455v2 |
| **Venue** | arXiv preprint (EMNLP 2021 version widely cited; not API-verified here) |
| **Cluster** | C6 — KG-grounded mitigation |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

A generate-then-refine pipeline. A token-level **fact critic** flags plausible sources of hallucination in a generated dialogue response; a refinement stage then retrieves correct entities by crafting a query signal propagated over the k-hop subgraph of a knowledge graph. Applies to any generated response without retraining the generator. Reports ~20.35% relative faithfulness improvement on OpenDialKG by FeQA.

## Inputs / outputs

**In:** a generated response + a KG. **Out:** a refined response with corrected entities.

## Strengths

- **The closest prior work to our KG-grounded correction**, and proof that KG-based entity repair works post-hoc without retraining.
- The token-level critic → refine split mirrors our detect → mitigate separation.
- k-hop subgraph retrieval is the mechanism we adopt for our NetworkX subgraphs.

## Limitations

- Corrects **entities**, not arbitrary propositions: it can fix 'Nolan directed Interstellar' → correct director, but not a numeric, temporal, or causal claim.
- Needs a KG that is already aligned to the dialogue domain (OpenDialKG); open-domain Wikidata is far sparser and noisier.
- No abstention: the refiner substitutes an entity rather than declining.
- Assumes the KG is correct and current. *(verify on full read)*

## Compute cost

A critic pass + k-hop subgraph retrieval + a refinement LM per response.

## Reusable for VeriFact

**Cited for our k-hop subgraph design and for post-hoc KG correction.** Our extensions over it: entity *and* non-entity claims, abstention when the KG is sparse, and never trusting the KG as sole authority.

## Threat to our novelty

Moderate on the KG-correction half. Differences to state plainly: open-domain rather than domain-aligned KG, abstention, and KG treated as one weighted signal.
