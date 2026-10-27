# wang2020minilm

| Field | Value |
|---|---|
| **Title** | MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers |
| **Authors** | Wang, Wei, Dong, Bao, Yang, Zhou (6 authors) |
| **Identifier** | arXiv:2002.10957v2 |
| **Venue** | arXiv preprint (NeurIPS 2020 version widely cited; not API-verified here) |
| **Cluster** | C5 — model compression |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Distils a large transformer into a small student by having the student deeply mimic the **self-attention module of the teacher's last layer**, including a new signal — the scaled dot-product between values — in addition to the usual attention distributions. Uses a teacher assistant for very large teachers.

## Inputs / outputs

**In:** a teacher model + corpus. **Out:** a much smaller student.

## Strengths

- Retains >99% of teacher accuracy on SQuAD 2.0 and several GLUE tasks with 50% of the parameters and compute.
- **The justification for running the whole system on CPU**, which is what makes this project demonstrable on a laptop without a GPU.

## Limitations

- Distillation is lossy in ways that are task-dependent; the headline retention figures are for GLUE/SQuAD, not for retrieval or NLI over long passages. *(verify on full read)*
- Gives no guarantee about calibration — a distilled model's confidence may be worse even where its accuracy holds, which matters directly for our calibration stage.

## Compute cost

N/A to us — we consume a released checkpoint.

## Reusable for VeriFact

Cited for the `all-MiniLM-L6-v2` embedding model and, more importantly, as the **documented justification of our CPU-only feasibility claim** in the non-functional requirements.

## Threat to our novelty

None.
