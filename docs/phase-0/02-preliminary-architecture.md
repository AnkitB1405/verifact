# Preliminary Architecture (for approval — nothing built yet)

## 1. Shape: one FastAPI service, a worker, Postgres, and a React dashboard

```
                 ┌─────────────┐
   client ─────► │  FastAPI    │  /api/v1/{analyze,verify,correct,results,feedback,health}
   (UI, bot)     │  app layer  │
                 └──┬───────┬──┘
                    │       │ enqueue (long jobs)
                    │       ▼
                    │   ┌──────────────────┐
                    │   │  Orchestrator    │  pipeline runner, per-claim budget policy
                    │   └──┬───┬───┬───┬───┘
                    │      │   │   │   │
       ┌────────────┘      │   │   │   └────────────────┐
       ▼                   ▼   │   ▼                    ▼
 ┌───────────┐     ┌───────────┐ ┌──────────────┐  ┌──────────────┐
 │ Input     │     │ Claim     │ │ Evidence     │  │ Verification │
 │ Processor │────►│ Extractor │ │ Retriever    │  │ Engine       │
 └───────────┘     └───────────┘ │  BM25+FAISS  │  │ sim│NLI│KG│rel│
                                 │  src registry│  └──────┬───────┘
                                 └──────┬───────┘         │
                                        ▼                 ▼
                                 ┌──────────────┐  ┌──────────────┐
                                 │ KG Module    │  │ Scoring +    │
                                 │ NetworkX /   │◄─┤ Calibration  │
                                 │ Wikidata     │  └──────┬───────┘
                                 └──────────────┘         ▼
                                                   ┌──────────────┐
                                                   │ Mitigation   │ (abstains)
                                                   └──────┬───────┘
                                                          ▼
                                                   ┌──────────────┐
   Postgres (runs, claims, evidence, verdicts,     │ Explanation  │
   feedback — JSONB for score breakdowns)  ◄───────┤ Assembler    │
                                                   └──────────────┘
```

**Why a worker/queue at all:** a 10-sentence input can be ~25 claims × (retrieval + NLI over
k passages). That is seconds to tens of seconds — too long for a synchronous HTTP request at
demo time. `POST /analyze` returns `202 + run_id`; `GET /results/{id}` polls. `POST /verify`
stays synchronous for a *single* claim (fast path, used by the UI and by integrators).
**Decision deferred:** Celery+Redis vs FastAPI `BackgroundTasks` + Postgres-row state.
Default = `BackgroundTasks` + Postgres (one less service). Revisit only if we need retries
across process restarts. → ADR-004.

## 2. Module contracts (the real interface list — P1 owns these files)

All in `contracts/` as Pydantic v2 models; every module depends on these, not on each other.

```
Document        : id, raw_text, normalized_text, sentences[Sentence], meta
Sentence        : idx, char_start, char_end, text
Claim           : id, sentence_idx, char_span, text, claim_type, entities[Entity],
                  temporal[TemporalRef], numerics[NumericRef], checkworthy: bool
Entity          : surface, char_span, label, kb_id|None, kb_confidence
EvidencePassage : id, claim_id, text, source_id, url, title, published_at|None,
                  retrieval_scores{bm25, dense, rrf}, snippet_span
Source          : id, name, kind, reliability_tier, base_reliability, recency_policy
KGCheck         : claim_id, triples_checked[Triple], status(SUPPORTED|CONTRADICTED|
                  MISSING|NOT_APPLICABLE), path_evidence, notes
ComponentScores : similarity, nli_entail, nli_contra, nli_neutral, source_reliability,
                  recency, cross_source_agreement, kg_consistency, evidence_coverage
Verdict         : claim_id, status(6), confidence, component_scores, calibrated: bool,
                  evidence_for[], evidence_against[], explanation, budget_spent
Correction      : claim_id, corrected_text|None, abstained: bool, abstain_reason|None,
                  citations[], max_supportable_confidence
AnalysisRun     : id, document, claims[], verdicts[], corrections[], annotated_text,
                  config_hash, model_versions, timings
```

**Rule:** contracts change only by PR to `contracts/`, reviewed by P1 + the affected owner.
A contract change that breaks another person's module must ship with that module's fix or a
deprecation shim. This is the single biggest coordination risk in a 4-person build.

## 3. Verification pipeline — the five stages, and what each produces

| Stage | Input | Output | Owner |
|---|---|---|---|
| S1 Semantic similarity | claim, k passages | cosine per passage, max + mean | P4 |
| S2 NLI | (passage=premise, claim=hypothesis) | 3-way probs per passage | P4 |
| S3 KG consistency | claim triples, KG | `KGCheck` | P3 |
| S4 Evidence reliability | passages + source registry | per-passage reliability × recency | P3 registry, P4 use |
| S5 Aggregation + status | all of the above | `Verdict` | P4 |

### S5 aggregation (documented, configurable, not a magic number)

For claim *c* with passages *i = 1..k*, per-passage weight

&nbsp;&nbsp;`w_i = r(source_i) · ρ(age_i) · relevance_i`

where `r ∈ (0,1]` from the source registry tier, `ρ` an exponential recency decay with a
per-source-type half-life, `relevance_i` the fused retrieval score. Then

&nbsp;&nbsp;`E = Σ w_i·p_entail,i / Σ w_i`  and  `C = Σ w_i·p_contra,i / Σ w_i`

Status rule (thresholds on the **dev** split, never test):

```
coverage < τ_cov                        → UNVERIFIABLE        (no usable evidence at all)
coverage ok, max(E,C) < τ_weak          → INSUFFICIENT_EVIDENCE
E - C >  τ_sup   and KG ∈ {SUPPORTED, MISSING, N/A}   → SUPPORTED
C - E >  τ_con   or  KG = CONTRADICTED                → CONTRADICTED
E,C both high (disagreement across sources)           → AMBIGUOUS
supported only by evidence older than claim's temporal scope, and a newer
   source disagrees                                   → OUTDATED
otherwise                                             → INSUFFICIENT_EVIDENCE
```

`confidence` is a **calibrated** score: raw `|E−C|` passed through isotonic regression (or
temperature scaling) fitted on the dev split; `Verdict.calibrated` records whether a fitted
calibrator was actually loaded. Uncalibrated output is never labelled a probability. ECE is
reported. → ADR-005.

### Adaptive budget (H2)
Pass 1 runs every claim at k=3 with a small NLI model. A claim is **escalated** to k=10 +
larger NLI if `|E−C|` is near a threshold, sources disagree, or the claim carries a numeric or
temporal reference. `budget_spent` is recorded per claim so the cost/accuracy curve is real.

## 4. Technology decisions — with the alternative and the cost

| Need | Choice | Alternatives rejected | Why | Cost |
|---|---|---|---|---|
| API | FastAPI + Pydantic v2 | Flask, Django REST | async I/O for fan-out retrieval; schemas = validation + OpenAPI for free | none material |
| ORM/migrations | SQLAlchemy 2.0 + Alembic | raw SQL, Tortoise | migrations are a marking criterion; mature | some boilerplate |
| DB | Postgres + JSONB | SQLite, Mongo | JSONB stores the score breakdown without 10 tables; relational for runs/claims | needs Docker |
| Sentences/NER | spaCy `en_core_web_trf` (fallback `_sm`) | pure LLM | deterministic, offline, free, reproducible | ~450MB model |
| Atomic claims | rule+dependency decomposition **first**; optional LLM decomposer behind a flag | LLM-only | LLM-only is non-reproducible and may need a paid key we may not have | LLM path optional |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | OpenAI embeddings | runs on CPU, 384-d, offline | quality ceiling |
| Lexical retrieval | `rank_bm25` | Elasticsearch | corpus is small; no extra service | O(n) scan |
| Vector index | FAISS flat (`IndexFlatIP`) | pgvector, Chroma, HNSW | corpus ≤ ~10^5 passages; flat is exact and zero-tuning | memory |
| Fusion | Reciprocal Rank Fusion | learned reranker | 3 lines, no training, strong baseline | — |
| NLI | `cross-encoder/nli-deberta-v3-small` (escalate: `-base`/`-large` if GPU) | zero-shot LLM | cheap, local, deterministic, has published behaviour | **GPU-dependent** |
| KG | **NetworkX** in-process + live Wikidata SPARQL (cached) | Neo4j, RDFLib+triplestore | per-claim subgraphs are tiny (≤ few hundred nodes); a graph DB buys nothing here. Migration path documented in ADR-003 | no persistence/graph queries at scale |
| Frontend | React + TypeScript + Vite + Tailwind | Next.js | SPA talking to our API; no SSR need, no second runtime to deploy | — |
| Viz | one dependency: `@xyflow/react` for the KG subgraph | d3 from scratch, cytoscape | least code for an evidence/KG graph view | bundle size |
| CI | GitHub Actions; ruff, mypy, pytest, bandit, pip-audit, Trivy | — | all required by the brief | runner minutes |

**Deliberately NOT used:** Kubernetes, Kafka, a feature store, a vector DB service, LangChain,
microservices. Each would add operational surface with no benefit at this scale, and each
would be something the student has to defend in the viva for no gain.

## 5. Security posture (threat-model summary, full doc in Phase 9)

| Threat | Control | Owner |
|---|---|---|
| Prompt injection via retrieved evidence | evidence passed as delimited data; prompts instruct ignore-imperatives; adversarial fixture in CI | P2 |
| SSRF via URL-based retrieval | allowlist of registry hostnames, DNS resolution checked against private ranges, no redirects off-allowlist, timeout + size cap | P3 |
| SQL injection | ORM only, no string-built SQL; `ruff` rule + review | P1 |
| Secrets in repo | `.env` only, `.env.example` committed, gitleaks in CI, pre-commit hook | P1 |
| DoS via huge input | max chars, max claims, request rate limit (slowapi), job timeout | P1 |
| Leaking input text in logs | structured logging with a redaction filter; raw text never at INFO | P1 |
| Unsafe error responses | central exception handler → typed error schema, no tracebacks to client | P1 |

## 6. Decisions requiring approval before Phase 1 ends

- **ADR-001** the contribution (H1/H2) — needs guide sign-off.
- **ADR-002** claim decomposition: rules-first, LLM optional. *Blocks P2.*
- **ADR-003** NetworkX over Neo4j. *Blocks P3.*
- **ADR-004** BackgroundTasks over Celery. *Blocks P1.*
- **ADR-005** calibration method and the status threshold policy. *Blocks P4.*
