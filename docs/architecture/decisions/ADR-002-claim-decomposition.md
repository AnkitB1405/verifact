# ADR-002 — Claim decomposition: rules first, LLM optional

- **Status:** Accepted · **Date:** 2026-10-29 · **Owner:** P2 (Bhuvi) · **Reviewed by:** P4

## Context

FActScore (`min2023factscore`) decomposes with an LLM and is the reference for atomic-fact
decomposition. Our brief requires reproducible results, forbids hardcoded or faked behaviour,
and leaves it uncertain whether a paid LLM key is available at all (`<<TBD>>`, initiation §5).
Decomposition quality bounds everything downstream: a claim that is split wrongly cannot be
verified correctly, and P4's metrics are computed over whatever P2 emits.

## Decision

**A deterministic, dependency-parse-based decomposer is the default and the only mandatory
path.** An LLM decomposer exists behind `extraction.llm_decomposer.enabled` (default `false`),
must return a validated schema, and falls back to the rules on any malformed output without
raising.

Our operational definition of *atomic*, which goes in the report verbatim:

> A claim is atomic when it asserts exactly one relation between resolved arguments, and
> removing any part of it destroys the assertion.

Five worked examples (also the test fixtures in `tests/fixtures/claims_golden.json`):

| Input sentence | Atomic claims |
|---|---|
| "Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911." | (1) Marie Curie won the Nobel Prize in Physics in 1903. (2) Marie Curie won the Nobel Prize in Chemistry in 1911. |
| "The Eiffel Tower, completed in 1889, is 330 metres tall." | (1) The Eiffel Tower was completed in 1889. (2) The Eiffel Tower is 330 metres tall. |
| "Python, which is slow but popular, was created by Guido van Rossum." | (1) Python was created by Guido van Rossum. *("slow but popular" is opinion → not check-worthy)* |
| "He later moved to Berlin." | (1) flagged **not standalone-interpretable** — unresolved "He" → routed to `AMBIGUOUS` |
| "Although many believe otherwise, the Great Wall is not visible from space." | (1) The Great Wall is not visible from space. *(the concessive clause is discourse, not a claim)* |

## Consequences

- Decomposition is reproducible and free, and the same input always yields the same claims
  (NFR-06).
- Quality will be **lower than an LLM decomposer's**, especially for coreference and implicit
  claims. This is a stated limitation, measured on a hand-annotated dev set, not hidden.
- Coreference is **not resolved**; unresolved referents are detected and flagged rather than
  guessed (FR-11). A guessed referent produces a confidently wrong verdict, which is worse
  than an honest `AMBIGUOUS`.
- P2 owns `claims_golden.json`; any change to the decomposer regenerates it in the same PR.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| LLM-only decomposition | non-reproducible, possibly unavailable, and it would put an unauditable model at the head of the pipeline |
| Fine-tune a decomposition model | no training data, no budget, no time |
| One claim per sentence, no decomposition | compound sentences would get a single verdict, defeating claim-level reporting — the exact failure FActScore identifies |
| Resolve coreference with a pretrained resolver | adds a model and a failure mode for a gain we cannot measure in one week; flagging is cheaper and safer |
