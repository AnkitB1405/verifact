# Project Initiation Document — VeriFact

**Title:** VeriFact: An Explainable AI Hallucination Detection and Mitigation Framework Using Trusted Sources and Knowledge Graphs
**Phase:** 0 (Initiation) — no implementation code written yet.
**Date:** 2026-11-01
**Team size:** 4

---

## 1. Problem statement (one paragraph)

Large language models emit fluent text whose factual claims may be unsupported, contradicted
by reliable sources, outdated, or fabricated. Consumers of that text cannot see *which*
sentence is unreliable or *why*. VeriFact takes AI-generated text, decomposes it into atomic
factual claims, retrieves evidence from a restricted registry of trusted sources, checks each
claim against that evidence with semantic retrieval, natural language inference, and a
structured knowledge graph, and returns a per-claim verification status with the evidence and
component scores that produced it. Where evidence is sufficient, it proposes a grounded
correction; where evidence is insufficient, it abstains.

## 2. In scope

- Claim-level decomposition of English prose (single-document, no multi-turn dialogue state).
- Evidence retrieval from a **closed, configurable source registry** (Wikipedia/Wikidata +
  Crossref + a local corpus; others only if added to the registry).
- Verification producing one of six statuses: `SUPPORTED`, `CONTRADICTED`, `UNVERIFIABLE`,
  `INSUFFICIENT_EVIDENCE`, `OUTDATED`, `AMBIGUOUS`.
- Per-claim explanation payload: evidence passages, source metadata, component scores.
- Evidence-grounded correction with abstention.
- REST API (FastAPI) + a dashboard.
- Measured evaluation against three baselines with ablations.

## 3. Explicitly out of scope

- Multilingual verification.
- Image/audio/video claims.
- Real-time streaming verification of token output.
- Training or fine-tuning our own NLI or extraction models (we use pretrained checkpoints;
  fine-tuning is listed as future scope).
- Open web search. Unrestricted web results are never treated as trustworthy.
- Any claim that the system establishes *truth*. It establishes *evidential support*.

## 4. Hard constraints we commit to

1. **Absence of evidence is never classified as falsehood.** It maps to `UNVERIFIABLE` or
   `INSUFFICIENT_EVIDENCE`.
2. **No fabricated results.** Every number in the report is traceable to a committed
   evaluation run with a logged config hash and seed. Unmeasured numbers are labelled
   *Expected* or *Proposed*, in a separate section.
3. **Component scores are never collapsed into one hidden number.** The aggregate is reported
   alongside its inputs and its formula is documented.
4. **Retrieved text is data, never instruction.** Evidence is passed to any LLM inside a
   delimited, role-separated block; the extraction/correction prompts ignore imperatives
   found inside evidence. This is tested with an adversarial prompt-injection fixture.
5. **Corrections never exceed their evidence.** Confidence of a correction is bounded above by
   the confidence of the evidence it cites; below a threshold the module abstains.
6. **No task is marked Done without a passing test and a tracked issue.**

## 5. Missing information — blocking Phase 12, not Phase 1

These were **not supplied** and must come from the student/guide before the academic
deliverables can be finalised. Nothing will be invented.

| # | Missing | Needed by |
|---|---------|-----------|
| 1 | Synopsis template (exact file) | Phase 12 |
| 2 | Complete project report template (exact file) | Phase 12 |
| 3 | University / department / course name, semester | Phase 12 |
| 4 | Names of the 4 team members + roll numbers (for role assignment and cover page) | Phase 4 |
| 5 | Guide's name and designation | Phase 12 |
| 6 | Submission deadlines (synopsis, mid-review, final) → drives sprint length | Phase 4 |
| 7 | GitHub org/repo to use, and whether branch protection is available on the plan | Phase 4 |
| 8 | Compute available: GPU? RAM? (decides NLI model size and whether DeBERTa-large is viable) | Phase 3 |
| 9 | Whether any paid LLM API key is permitted (decides LLM-based claim extraction vs spaCy-only) | Phase 3 |
| 10 | Whether internet access is available during the live demo (decides offline snapshot caching) | Phase 3 |

Placeholders in docs use the literal token `<<TBD: …>>` so they are greppable before submission.

## 6. Phase 0 exit criteria

- [x] Project initiation document (this file)
- [x] Research plan — `01-research-plan.md`
- [x] Preliminary architecture — `02-preliminary-architecture.md`
- [x] Agile backlog (10 epics, stories, sprint plan) — `03-agile-backlog.md`
- [x] Four-person work division with contribution sequence — `../team/` + `04-work-division.md`
- [ ] **Guide/student approval of the architecture and the novelty claim** ← we stop here

## 7. What the student must be able to explain before Phase 1 starts

1. Why "no evidence found" is not the same as "false", and what statuses encode that.
2. The difference between *truth* and *evidential support*, and which one this system measures.
3. Why the source registry is closed rather than an open web search.
4. Why component scores are kept separate from the aggregate.
5. The six verification statuses and one example sentence for each.
