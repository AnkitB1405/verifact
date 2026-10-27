# li2023halueval

| Field | Value |
|---|---|
| **Title** | HaluEval: A Large-Scale Hallucination Evaluation Benchmark for Large Language Models |
| **Authors** | Li, Cheng, Zhao, Nie, Wen (5 authors) |
| **Identifier** | arXiv:2305.11747v3 |
| **Venue** | arXiv preprint (EMNLP 2023 version widely cited; not API-verified here) |
| **Cluster** | C1 / evaluation |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

A large collection of generated and human-annotated hallucinated samples, built by a ChatGPT-based **sampling-then-filtering** two-step framework plus human labelling of real ChatGPT responses. Reports that ChatGPT fabricated unverifiable information in about 19.5% of responses in their setting, and that existing LLMs struggle to recognise hallucination in text — though providing external knowledge or adding reasoning steps helps.

## Inputs / outputs

**In:** a (question, response) pair. **Out:** hallucinated / not.

## Strengths

- **Directly on-task**: detecting hallucination in machine-generated text, which is our actual input distribution, unlike FEVER's mutated claims.
- The finding that external knowledge improves recognition is empirical support for our retrieval-centred design.
- The 19.5% fabrication figure is a citable statement of problem scale for the introduction.

## Limitations

- Labels are largely ChatGPT-generated then filtered, so the hallucination distribution reflects one model family's failure modes.
- Binary labels: no contradicted/unverifiable/outdated distinction, so our richer status set cannot be fully evaluated on it.
- No gold evidence annotations, so Recall@k is not measurable here. *(verify on full read)*
- Licence must be checked before use (GitHub: RUCAIBox/HaluEval).

## Compute cost

N/A.

## Reusable for VeriFact

**Secondary evaluation set for the detection task** (binary: flagged vs not), complementing FEVER's claim-level evaluation with gold evidence. Our hand-built `verifact-stress` set remains the only source for OUTDATED and AMBIGUOUS.

## Threat to our novelty

None — a benchmark.
