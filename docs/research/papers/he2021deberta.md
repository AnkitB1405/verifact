# he2021deberta

| Field | Value |
|---|---|
| **Title** | DeBERTa: Decoding-enhanced BERT with Disentangled Attention |
| **Authors** | He, Liu, Gao, Chen (4 authors) |
| **Identifier** | arXiv:2006.03654v6 |
| **Venue** | arXiv preprint (ICLR 2021 version widely cited; not API-verified here) |
| **Cluster** | C5 — the NLI backbone we use |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Two changes to BERT/RoBERTa. **Disentangled attention:** each token is represented by separate content and position vectors, and attention is computed with disentangled matrices over content and relative position. **Enhanced mask decoder:** absolute positions are injected at the decoding layer for masked-token prediction. Plus virtual adversarial training for fine-tuning.

## Inputs / outputs

**In:** text (pair). **Out:** contextual representations; fine-tuned for classification tasks such as MNLI.

## Strengths

- Reports +0.9 on MNLI over RoBERTa-large (90.2 → 91.1) with half the training data, and was the first single model to pass the human SuperGLUE macro-average.
- **MNLI performance is the number that matters to us**, since our NLI stage is an MNLI-style 3-way classifier.
- Small/base checkpoints are released, so a CPU-viable variant exists.

## Limitations

- A pretrained encoder, not a verification method. Everything about evidence handling is still ours.
- Published MNLI figures are for the **large** model; our small checkpoint will be meaningfully weaker and we must not quote the large number as if it were ours.
- Inherits NLI's well-known weaknesses: sensitivity to lexical overlap, poor handling of numbers and negation, and training on short sentence pairs rather than long retrieved passages. *(verify on full read)*

## Compute cost

`nli-deberta-v3-small`-class models run on CPU at a usable speed; large needs a GPU. This is the decision point for our adaptive-budget escalation.

## Reusable for VeriFact

**The backbone of verification stage S2.** Cited for the architecture; the specific fine-tuned cross-encoder checkpoint is cited separately in the implementation chapter.

## Threat to our novelty

None — a component we consume.
