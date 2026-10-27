# gao2023alce

| Field | Value |
|---|---|
| **Title** | Enabling Large Language Models to Generate Text with Citations |
| **Authors** | Gao, Yen, Yu, Chen (4 authors) |
| **Identifier** | arXiv:2305.14627v2 |
| **Venue** | arXiv preprint (EMNLP 2023 version widely cited; not API-verified here) |
| **Cluster** | C4 — citation generation and evaluation |
| **Metadata** | verified via arXiv API on 2026-11-02 |
| **Summary source** | published abstract |
| **Full text read by** | `<<TBD>>` — items marked *(verify on full read)* are inferences from the abstract, not quotations |

## Core method

Introduces ALCE, a benchmark for automatic evaluation of LLM citations: a set of questions plus retrieval corpora, requiring end-to-end systems that retrieve evidence and answer with citations. Defines automatic metrics on three axes — fluency, correctness, citation quality — and reports strong correlation with human judgement.

## Inputs / outputs

**In:** a question + corpus. **Out:** an answer with inline citations, scored on three axes.

## Strengths

- **Citation quality as a measurable axis**, which is what our mitigation module must be judged on rather than on fluency.
- Deliberately uses fixed retrieval corpora instead of a commercial search engine so results are reproducible — the same reasoning behind our closed source registry.
- Finding that even the best models lack complete citation support 50% of the time on ELI5 is a useful honesty anchor.

## Limitations

- Evaluates generation-with-citations, not verification of someone else's text.
- Benchmark, not a method.
- Metrics are built around an answer to a question, so they do not transfer unchanged to arbitrary input prose. *(verify on full read)*

## Compute cost

N/A.

## Reusable for VeriFact

**The source of our citation-quality metric for corrections**, and an independent argument for reproducible fixed corpora over live web search.

## Threat to our novelty

None — complementary evaluation work.
