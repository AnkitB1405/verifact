# Software Requirements Specification — VeriFact

| | |
|---|---|
| **Project** | VeriFact: An Explainable AI Hallucination Detection and Mitigation Framework Using Trusted Sources and Knowledge Graphs |
| **Version** | 1.0 (Phase 2) |
| **Date** | 2026-10-28 |
| **Authors** | P1 (Ankit) — §1–3, 5–8; P4 (Bhavish) — §4 status semantics, §6 quality requirements |
| **Institution** | `<<TBD: university / department / course>>` |

---

## 1. Purpose and scope

VeriFact accepts AI-generated text and reports, **per factual claim**, whether that claim is
attributable to a restricted registry of trusted sources, with the evidence and the component
scores that produced the decision, and proposes an evidence-grounded correction where the
evidence supports one.

**It measures attribution to trusted sources. It does not determine truth.** Every
requirement below is to be read in that light.

### 1.1 In scope
English prose; single-document input; a closed, configurable source registry; claim-level
verdicts over six statuses; per-claim explanation; grounded correction with abstention; a REST
API; a dashboard; and a reproducible evaluation against three baselines.

### 1.2 Out of scope
Multilingual input; non-text claims; streaming/token-level verification; training or
fine-tuning models; open web search; multi-turn dialogue state; and any claim that the system
establishes truth.

### 1.3 Definitions

| Term | Definition used throughout |
|---|---|
| **Hallucination** | Generated content that conflicts with, or cannot be attributed to, established external knowledge. VeriFact targets the *fact-conflicting* class (`zhang2023siren`); it does not address self-contradiction within a passage. |
| **Claim** | An atomic, standalone-interpretable factual proposition extracted from a sentence (after `min2023factscore`, `rashkin2021attribution`). |
| **Check-worthy** | A claim that asserts a verifiable fact about the external world, as opposed to an opinion, instruction, question or rhetorical statement. |
| **Evidence passage** | A span of text retrieved from a registered source, with its source id, URL, title and publication date where available. |
| **Source registry** | The configured set of permitted sources, each with a reliability tier and a recency policy. |
| **Verdict** | One of six statuses plus a calibrated confidence and the component scores behind it. |
| **Abstention** | The mitigation module declining to produce a correction because evidence is insufficient. |

---

## 2. Stakeholders and user classes

| Class | Needs | Priority |
|---|---|---|
| **End user** (reads AI output) | see which sentences are unreliable and why, with sources | must |
| **Integrator** (chatbot / LLM app) | a stable REST API, predictable latency, machine-readable verdicts | must |
| **Evaluator / examiner** | reproducible results, traceable decisions, measured metrics | must |
| **Developer / maintainer** | modular code, contracts, tests, docs | must |
| **Source operator** (Wikipedia, Crossref) | polite, rate-limited, cached access | must |

---

## 3. Functional requirements

Each FR has an id, a priority (M = must, S = should, C = could), the owning epic, the module,
and the test that proves it. **An FR with no test is not satisfied.**

### 3.1 Input processing (EPIC 3, P2)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-01 | Accept plain UTF-8 text up to a configured maximum length | M | `test_input.py::test_max_length` |
| FR-02 | Reject empty or whitespace-only input with a typed validation error, not a 500 | M | `test_input.py::test_empty_rejected` |
| FR-03 | Normalise whitespace, unicode (NFKC) and line endings without altering character offsets into the normalised text | M | `test_input.py::test_offset_invariant` |
| FR-04 | Split input into sentences, preserving `char_start`/`char_end` such that slicing the normalised text reproduces each sentence exactly | M | `test_input.py::test_offset_invariant` |
| FR-05 | Assign every sentence and claim a stable id so the annotated output can be mapped back to the original | M | `test_input.py::test_ids_stable` |
| FR-06 | Accept a declared "as of" date for the input, so temporal claims can be judged against the right horizon | S | `test_input.py::test_asof` |

### 3.2 Claim extraction (EPIC 3, P2)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-07 | Extract atomic factual claims from each sentence, splitting coordinated and subordinated propositions | M | `test_extraction.py::test_decomposition` |
| FR-08 | Extract named entities, dates and numeric values per claim, with character spans | M | `test_extraction.py::test_entities` |
| FR-09 | Classify each claim as check-worthy or not, excluding opinions, instructions, questions and rhetoric | M | `test_extraction.py::test_checkworthiness` |
| FR-10 | Preserve claim → sentence → original-text mapping for every claim | M | `test_extraction.py::test_mapping` |
| FR-11 | Flag a claim as not standalone-interpretable when it contains an unresolved referent, so it can reach `AMBIGUOUS` rather than a wrong verdict | M | `test_extraction.py::test_unresolved_referent` |
| FR-12 | Support an optional LLM-based decomposer behind a configuration flag, validating its structured output and falling back to rules on malformed output without raising | C | `test_extraction.py::test_llm_fallback` |

### 3.3 Evidence retrieval (EPIC 4, P3)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-13 | Retrieve evidence only from sources present in the configured registry | M | `test_registry.py::test_closed_registry` |
| FR-14 | Assign every source a reliability tier; an unregistered source is assigned the lowest tier and logged, never silently discarded | M | `test_registry.py::test_unknown_source_lowest_tier` |
| FR-15 | Support lexical (BM25) and dense (embedding) retrieval and fuse the rankings | M | `test_retrieval.py::test_fusion` |
| FR-16 | Record for each passage: source id, URL, title, publication date where available, and the component retrieval scores | M | `test_retrieval.py::test_metadata` |
| FR-17 | Cache external responses and respect per-source rate limits and timeouts | M | `test_clients.py::test_cache_and_timeout` |
| FR-18 | Operate from a local snapshot with outbound network disabled | S | `test_offline.py::test_offline_pipeline` |
| FR-19 | Block requests to non-allowlisted hosts and to addresses resolving into private or link-local ranges | M | `tests/security/test_ssrf.py` |

### 3.4 Knowledge graph (EPIC 5, P3)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-20 | Link claim entities to knowledge-base identifiers with a confidence score | M | `test_linking.py::test_link_confidence` |
| FR-21 | Return a candidate list rather than one silent choice when a mention is ambiguous | M | `test_linking.py::test_ambiguous_candidates` |
| FR-22 | Build a bounded k-hop subgraph per claim, with a configured node cap | M | `test_kg.py::test_node_cap` |
| FR-23 | Map a claim to (subject, predicate, object) triples for a documented set of supported predicates; return `NOT_APPLICABLE` for unsupported predicates | M | `test_kg.py::test_not_applicable` |
| FR-24 | Distinguish `SUPPORTED`, `CONTRADICTED`, `MISSING` and `NOT_APPLICABLE`; an absent relation must yield `MISSING` | M | `test_kg.py::test_missing_is_not_contradicted` |
| FR-25 | Return the graph path used, so the decision is inspectable | M | `test_kg.py::test_path_returned` |

### 3.5 Verification engine (EPIC 6, P4)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-26 | Compute semantic similarity between claim and each passage | M | `test_similarity.py` |
| FR-27 | Compute 3-way NLI (entail / contradict / neutral) with the passage as premise and the claim as hypothesis | M | `test_nli.py::test_direction` |
| FR-28 | Weight each passage by source reliability × recency decay × retrieval relevance | M | `test_weighting.py` |
| FR-29 | Aggregate into exactly one of the six statuses per the documented decision rule | M | `test_aggregate.py::test_all_statuses_reachable` |
| FR-30 | Never return `CONTRADICTED` when no evidence was retrieved | M | `test_aggregate.py::test_no_evidence_is_unverifiable` |
| FR-31 | Retain and expose every component score on the verdict | M | `test_aggregate.py::test_components_present` |
| FR-32 | Report a calibrated confidence, and flag explicitly whether a fitted calibrator was used | M | `test_calibrate.py::test_flag_honest` |
| FR-33 | Allocate extra retrieval and a larger inference model to claims that are uncertain, numeric, temporal, or backed by disagreeing sources; record the budget spent | S | `test_budget.py::test_escalation` |
| FR-34 | Deduplicate near-identical passages before computing cross-source agreement | S | `test_weighting.py::test_dedup` |

### 3.6 Explainability (EPIC 7, P4)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-35 | For every claim, expose: original sentence, extracted claim, status, supporting evidence, contradicting evidence, source metadata, component scores, final confidence, and a natural-language explanation | M | `test_explain.py::test_payload_complete` |
| FR-36 | The explanation must name the component that decided the status | M | `test_explain.py::test_names_deciding_component` |

### 3.7 Correction and mitigation (EPIC 7, P2)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-37 | Generate a correction only from cited retrieved evidence | M | `test_corrector.py::test_citations_present` |
| FR-38 | Abstain, with a recorded reason, when evidence is insufficient | M | `test_corrector.py::test_abstains` |
| FR-39 | Introduce no claim that is not supported by a cited passage | M | `test_corrector.py::test_no_new_claims` |
| FR-40 | Cap a correction's confidence at the confidence of the evidence supporting it | M | `test_corrector.py::test_confidence_cap` |
| FR-41 | Re-verify a generated correction through the ordinary pipeline and discard it if it does not come back supported | S | `test_corrector.py::test_self_check` |
| FR-42 | Produce an annotated version of the original text with problematic spans marked, aligned to the original offsets | M | `test_annotate.py::test_spans_align` |

### 3.8 API (EPIC 8, P1)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-43 | `POST /api/v1/analyze` — full pipeline on a document; returns `202` + run id | M | `tests/api/test_analyze.py` |
| FR-44 | `POST /api/v1/verify` — synchronous verification of a single claim | M | `tests/api/test_verify.py` |
| FR-45 | `POST /api/v1/correct` — correction for a verified claim or run | M | `tests/api/test_correct.py` |
| FR-46 | `GET /api/v1/health` — liveness plus component and model-version report | M | `tests/api/test_health.py` |
| FR-47 | `GET /api/v1/results/{id}` — stored run, including partial results for a run still in progress | M | `tests/api/test_results.py` |
| FR-48 | `POST /api/v1/feedback` — user feedback bound to a run and claim | M | `tests/api/test_feedback.py` |
| FR-49 | Versioned URL prefix; an OpenAPI document is published | M | `tests/api/test_openapi.py` |
| FR-50 | API-key authentication on all non-health endpoints | M | `tests/api/test_auth.py` |
| FR-51 | Per-key rate limiting returning `429` | M | `tests/api/test_ratelimit.py` |
| FR-52 | Errors return a typed error body with no traceback and no echo of input text | M | `tests/api/test_errors.py` |

### 3.9 Dashboard (EPIC 8, P2)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-53 | Enter text and run an analysis | M | manual script + `test_ui_smoke.py` |
| FR-54 | Claim-level result list with status and confidence | M | `test_ui_smoke.py` |
| FR-55 | Inspect supporting and contradicting evidence with source and date | M | `test_ui_smoke.py` |
| FR-56 | Show component scores for a claim; every number on screen must come from the API payload | M | `test_ui_smoke.py` |
| FR-57 | Highlight problematic spans in the original text | M | `test_ui_smoke.py` |
| FR-58 | Show original vs corrected text side by side with citations | M | `test_ui_smoke.py` |
| FR-59 | Export the verification report as JSON, re-importable | S | `test_export.py` |
| FR-60 | Show the KG subgraph and path used for a claim | C | manual |

### 3.10 Persistence (EPIC 2, P1)

| id | Requirement | Pri | Test |
|---|---|---|---|
| FR-61 | Persist runs, claims, evidence, verdicts, corrections and feedback | M | `tests/integration/test_persistence.py` |
| FR-62 | Record per run: config hash, model identifiers and versions, stage timings | M | `tests/integration/test_persistence.py::test_run_provenance` |
| FR-63 | Schema changes are applied by migration, reversible by one step | M | CI job `migrations` |

---

## 4. Non-functional requirements

Numbers are **targets to be measured in Phase 10**, not claims. Each will be reported as
measured, or reported as missed.

| id | Requirement | Target | How measured |
|---|---|---|---|
| NFR-01 | Single-claim verification latency, warm models, CPU | p50 ≤ 2.5 s, p95 ≤ 6 s | `eval/bench_latency.py` |
| NFR-02 | 10-sentence document analysis, end to end, CPU | p50 ≤ 60 s | same |
| NFR-03 | Memory ceiling with all models loaded | ≤ 4 GB RSS | `/usr/bin/time -v` in CI |
| NFR-04 | Runs on CPU only, no GPU required | hard requirement | CI runs on CPU runners |
| NFR-05 | Full pipeline functions with outbound network disabled, from a local snapshot | hard requirement | `test_offline.py` |
| NFR-06 | Identical input + config + seed produces identical verdicts | bitwise identical statuses and scores to 6 dp | `test_determinism.py` |
| NFR-07 | Test coverage on `src/` | ≥ 70% line | CI gate |
| NFR-08 | Every public function typed; mypy clean on `src/` | 0 errors | CI gate |
| NFR-09 | Lint clean | ruff, 0 findings | CI gate |
| NFR-10 | No high/critical dependency vulnerabilities at release | 0 unaddressed | pip-audit in CI |
| NFR-11 | No secret ever committed | 0 findings | gitleaks in CI |
| NFR-12 | External source politeness | ≤ 1 req/s per source, cached, identifying User-Agent | `test_clients.py` |
| NFR-13 | A new developer can install and run from the docs alone | ≤ 30 min on a clean machine | dry run by a team member who did not write the doc |
| NFR-14 | Confidence calibration | ECE reported; post-calibration ECE ≤ pre-calibration ECE on test | `eval/harness.py` |
| NFR-15 | Logs contain no raw input text at INFO or above | hard requirement | `test_logging.py::test_redaction` |

---

## 5. Constraints

| id | Constraint |
|---|---|
| C-01 | Python 3.13; CPU-only; no paid API required for any mandatory feature |
| C-02 | Evidence sources limited to the registry; **unrestricted web search is prohibited** |
| C-03 | LLM use is optional and confined to decomposition and correction drafting; **an LLM is never in the verdict decision path** |
| C-04 | Retrieved content is data, never instruction (see §7) |
| C-05 | Secrets only via environment; nothing in the repository |
| C-06 | Datasets used must have a verified permissive licence |
| C-07 | Timeline: one week of build; see `scripts/TIMELINE.md` |

## 6. Assumptions and dependencies

| id | Assumption | If it fails |
|---|---|---|
| A-01 | Wikipedia/Wikidata APIs are reachable during development | offline snapshot mode (FR-18) covers the demo |
| A-02 | Pretrained NLI and embedding checkpoints are downloadable once, then cached | the `lexical` fallback backend keeps the pipeline and tests working, with degraded quality that must be reported as such |
| A-03 | The input text is in English | out of scope otherwise; input is not language-detected in v1 — recorded in Known Limitations |
| A-04 | Claims are mostly encyclopaedic | coverage drops sharply for niche or private facts, correctly surfacing as `UNVERIFIABLE` |

## 7. Security requirements

| id | Requirement | Test |
|---|---|---|
| SR-01 | Treat all input text, all retrieved content and all LLM output as untrusted | `tests/security/` |
| SR-02 | Retrieved evidence is passed to any LLM inside a delimited data block; imperative content inside evidence must not change behaviour | `test_prompt_injection.py` |
| SR-03 | Outbound requests restricted to allowlisted hosts; private/link-local resolution blocked; no off-allowlist redirects; response size and time capped | `test_ssrf.py` |
| SR-04 | All database access through the ORM; no string-built SQL | `ruff` + review |
| SR-05 | Input size, claim count and request rate bounded | `test_ratelimit.py`, `test_input.py` |
| SR-06 | Error responses carry no stack trace and no echo of input | `test_errors.py` |
| SR-07 | Logs redact raw input text | `test_logging.py` |
| SR-08 | Secrets from environment only; `.env` git-ignored; `.env.example` committed | gitleaks |

## 8. Traceability

| Epic | FRs | Module | Owner |
|---|---|---|---|
| 2 Architecture & data | FR-61…63 | `db/`, `contracts/` | P1 |
| 3 Claim extraction | FR-01…12 | `input/`, `extraction/` | P2 |
| 4 Evidence retrieval | FR-13…19 | `retrieval/` | P3 |
| 5 Knowledge graph | FR-20…25 | `kg/` | P3 |
| 6 Verification | FR-26…34 | `verification/` | P4 |
| 7 Explain & mitigate | FR-35…42 | `explain/`, `mitigation/` | P4, P2 |
| 8 API & UI | FR-43…60 | `api/`, `web/` | P1, P2 |
| 9 Testing & security | SR-01…08, NFR-07…11 | `tests/` | all |
| 10 Evaluation | NFR-01…03, NFR-14 | `eval/` | P4 |

**Coverage check:** 63 FRs, 15 NFRs, 8 SRs. Every FR names a test. Any FR whose test does not
exist at submission time must be moved to Known Limitations, not quietly dropped.
