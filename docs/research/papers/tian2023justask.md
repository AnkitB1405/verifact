# tian2023justask

| Field | Value |
|---|---|
| **Title** | Just Ask for Calibration: Strategies for Eliciting Calibrated Confidence Scores from Language Models Fine-Tuned with Human Feedback |
| **Authors** | Tian, Mitchell, Zhou, Sharma, Rafailov, Yao, Finn, Manning (8 authors) |
| **Identifier** | arXiv:2305.14975v2 |
| **Venue** | arXiv preprint (EMNLP 2023 version widely cited; not API-verified here) |
| **Cluster** | C7 — calibration of LLMs |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Evaluates ways of extracting confidence from RLHF-tuned LLMs. Finds that **verbalised confidences emitted as output tokens** are typically better calibrated than the model's own conditional probabilities for models such as ChatGPT, GPT-4 and Claude, often halving expected calibration error relative to the conditional probabilities.

## Inputs / outputs

**In:** a question. **Out:** an answer plus a confidence, elicited by prompting rather than read from logits.

## Strengths

- Counter-intuitive and well-scoped result; a good example for the viva of why confidence must be measured rather than assumed.
- Reinforces that RLHF-tuned model probabilities are untrustworthy, which supports our decision to keep the LLM out of the decision path entirely.

## Limitations

- About LLM self-reported confidence, which our scoring stage deliberately does not use.
- Verbalised confidence is still the model's opinion of itself, with no external evidence behind it. *(verify on full read)*
- Results are model- and prompt-specific.

## Compute cost

One LLM call per item.

## Reusable for VeriFact

Cited in the methodology chapter as the **alternative calibration route we rejected**: we calibrate an evidence-based score on a held-out set rather than asking a model how sure it is. This is a deliberate, citable design choice.

## Threat to our novelty

None.
