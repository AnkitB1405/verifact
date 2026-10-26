# Agile Backlog & Sprint Plan

Platform: GitHub Issues + one Project board (columns: Backlog → Sprint → In Progress →
In Review → Done). Labels: `epic:1..10`, `owner:p1..p4`, `type:story|task|spike|bug|doc`,
`size:S|M|L`, `blocked`. Jira: evaluated, not adopted — not required and adds a second
source of truth. (Recorded as ADR-006.)

Estimation: 1 point ≈ half a day of one person. Velocity assumption **28 pts/sprint for the
team** (4 × 7) — recalibrated after Sprint 1 with actuals.

Sprint length: **1 week**, 8 sprints. Shift if deadlines differ → `<<TBD: deadlines>>`.

## Definition of Done (applies to every story, no exceptions)

1. Code merged via PR, reviewed and approved by someone who did not write it.
2. Unit tests for the new logic; CI green (ruff, mypy, pytest, bandit, pip-audit).
3. Contracts respected; if contracts changed, the PR updates `contracts/CHANGELOG.md`.
4. Docstrings on public functions; module doc updated in `docs/design/`.
5. Issue closed by the PR with `Closes #n`.
6. **The owner can explain it out loud** — recorded as a 3-bullet note in their
   `team/<person>/explainer-log.md`.

---

## Epics → stories

### EPIC 1 — Research & Requirements (P4 lead, all contribute)
| id | Story | Pts | Owner | Acceptance criteria |
|----|-------|-----|-------|---------------------|
| 1.1 | Survey 18+ papers into per-paper records | 8 | all (≥4 each) | 18 files in `docs/research/papers/`, each with DOI + limitations |
| 1.2 | Build gap matrix | 3 | P4 | matrix covers all surveyed systems × 10 capability columns |
| 1.3 | Write novelty statement + ADR-001 | 2 | P4 | states H1/H2, falsification criteria, approved by guide |
| 1.4 | SRS: functional + non-functional requirements | 5 | P1 | every FR traceable to an epic; NFRs have numbers (latency, input size) |
| 1.5 | Define the 6 statuses with examples | 2 | P4 | one worked example sentence per status, in SRS |

### EPIC 2 — Architecture & Data Model (P1 lead)
| 2.1 | Publish `contracts/` Pydantic models | 5 | P1 | all 11 models importable; `pytest contracts/` passes round-trip tests |
| 2.2 | DB schema + first Alembic migration | 5 | P1 | ER diagram matches migration; `alembic upgrade head` on clean DB |
| 2.3 | Repo skeleton, config (pydantic-settings), logging, exception handler | 5 | P1 | `make dev` boots; `/health` returns 200 |
| 2.4 | Docker + docker-compose (api, db) | 3 | P1 | `docker compose up` yields a working `/health` |
| 2.5 | Architecture document + C4-level diagrams | 3 | P1 | diagrams regenerated from the real module list |

### EPIC 3 — Claim Extraction (P2 lead)
| 3.1 | Input processing: validate, normalise, split sentences, keep char offsets | 5 | P2 | offsets round-trip: every sentence slice equals original substring |
| 3.2 | Entity/date/number extraction | 5 | P2 | ≥0.8 F1 on a 50-sentence hand-annotated dev set |
| 3.3 | Atomic claim decomposition (rules) | 8 | P2 | compound sentences split; mapping claim→sentence→char span preserved |
| 3.4 | Check-worthiness filter (fact vs opinion/rhetoric) | 5 | P2 | opinions excluded on a 60-item labelled set; FN rate reported |
| 3.5 | Optional LLM decomposer behind flag, with schema validation + malformed-output handling | 5 | P2 | invalid JSON → fallback to rules, logged, never crashes; injection fixture passes |

### EPIC 4 — Evidence Retrieval (P3 lead)
| 4.1 | Source registry (YAML) + reliability tiers + policy loader | 3 | P3 | tiers documented with justification; unknown source → lowest tier, not rejected silently |
| 4.2 | Wikipedia/Wikidata client with cache + SSRF guards | 5 | P3 | allowlist enforced; private-IP resolution blocked (unit test) |
| 4.3 | Crossref client; local-corpus loader | 3 | P3 | metadata incl. `published_at` where available |
| 4.4 | BM25 + FAISS + RRF fusion retriever | 8 | P3 | Recall@5 measured on FEVER dev subset and recorded |
| 4.5 | Offline snapshot mode for the demo | 3 | P3 | full pipeline runs with network disabled |

### EPIC 5 — Knowledge Graph (P3 lead)
| 5.1 | Entity linking to Wikidata QIDs with confidence + ambiguity handling | 8 | P3 | ambiguous mention → candidate list, not a silent pick |
| 5.2 | Per-claim subgraph construction (NetworkX) | 5 | P3 | subgraph ≤ N nodes; build time logged |
| 5.3 | Claim→triple mapping for a documented relation set | 8 | P3 | supported relations listed; unsupported → `NOT_APPLICABLE` |
| 5.4 | KG consistency check → `KGCheck` | 5 | P3 | `MISSING` ≠ `CONTRADICTED`; tested |
| 5.5 | KG staleness handling + ADR-003 migration path | 3 | P3 | stale/undated KG facts cannot alone produce CONTRADICTED |

### EPIC 6 — Verification Engine (P4 lead)
| 6.1 | S1 similarity stage | 3 | P4 | per-passage scores in `ComponentScores` |
| 6.2 | S2 NLI stage + model registry/versions | 8 | P4 | label mapping tested; model id recorded in run |
| 6.3 | S4 reliability × recency weighting | 5 | P4 | formula matches architecture doc; half-lives configurable |
| 6.4 | S5 aggregation + 6-status decision rule | 8 | P4 | thresholds in config; every status reachable in tests |
| 6.5 | Calibration (isotonic/temperature) + ECE | 5 | P4 | `calibrated` flag honest; ECE reported pre/post |
| 6.6 | Adaptive budget policy | 5 | P4 | `budget_spent` recorded; escalation triggers unit-tested |
| 6.7 | Orchestrator wiring all stages | 5 | P1+P4 | end-to-end run on a 5-sentence input |

### EPIC 7 — Scoring, Mitigation, Explainability (P2 lead for mitigation, P4 for scoring)
| 7.1 | Explanation assembler (human-readable, per claim) | 5 | P4 | explanation names the deciding component |
| 7.2 | Correction generation grounded in cited evidence | 8 | P2 | every correction cites ≥1 passage it is entailed by |
| 7.3 | Abstention policy | 3 | P2 | abstains below threshold; reason recorded |
| 7.4 | Correction self-check (re-verify the correction) | 5 | P2 | correction that fails re-verification is discarded |
| 7.5 | Annotated-text renderer (original with inline flags) | 3 | P2 | spans align with original offsets |

### EPIC 8 — API & Frontend (P1 API, P2 UI)
| 8.1 | 6 endpoints + versioning + OpenAPI | 8 | P1 | contract tests per endpoint; 202+run_id for analyze |
| 8.2 | Auth (API key) + rate limiting | 3 | P1 | 429 on limit; key from env |
| 8.3 | Feedback endpoint + storage | 3 | P1 | feedback linked to claim+run |
| 8.4 | Dashboard: input → run → claim list → status chips | 8 | P2 | happy path usable without reading docs |
| 8.5 | Evidence inspector + component-score panel + KG subgraph view | 8 | P2 | every number on screen traceable to the API payload |
| 8.6 | Original vs corrected diff view | 5 | P2 | side-by-side with citations |
| 8.7 | Export report (PDF/JSON) | 3 | P2 | JSON export re-importable |

### EPIC 9 — Testing & Security (P1 lead, everyone writes their own tests)
| 9.1 | Pytest infra, factories, coverage gate | 3 | P1 | coverage reported; gate ≥70% on `src/` |
| 9.2 | Integration tests across modules with fixtures | 5 | P1 | no network in CI (recorded fixtures) |
| 9.3 | API tests | 3 | P1 | all endpoints, incl. error paths |
| 9.4 | Security: bandit, pip-audit, gitleaks, Trivy | 3 | P1 | all wired, findings triaged not suppressed |
| 9.5 | Prompt-injection + SSRF adversarial test suite | 5 | P2+P3 | documented attack cases, all blocked |
| 9.6 | Test plan + test report documents | 3 | P1 | report contains real run output |

### EPIC 10 — Evaluation, Deployment, Documentation (P4 eval, P1 deploy)
| 10.1 | Build `verifact-stress` (120 items, 7 categories, 2-person review) | 8 | all | every item has gold status + gold evidence + reviewer |
| 10.2 | Baselines A/B/C implemented | 8 | P4 | same interface as proposed system; frozen configs |
| 10.3 | Evaluation harness: P/R/F1, accuracy, AUROC, ECE, Recall@k, latency, throughput | 8 | P4 | single command reproduces all tables; seeds+config hash logged |
| 10.4 | Ablations (−KG, −reliability, −calibration, −adaptive) | 5 | P4 | one row per ablation |
| 10.5 | Error analysis: FP/FN, source disagreement, no-evidence cases | 5 | P4 | ≥20 analysed cases with categories |
| 10.6 | CI/CD pipeline complete + documented | 5 | P1 | no `continue-on-error` masking failures |
| 10.7 | Deployment guide, install guide, user manual, known limitations | 5 | P1+P2 | a stranger can install from the doc alone |
| 10.8 | Synopsis + full report assembly | 8 | all | follows supplied templates `<<TBD: templates>>` |
| 10.9 | 50 viva Q&A + demo script | 5 | all (≈13 each) | answers in the owner's own words |

Total ≈ 262 pts ≈ 9.4 team-sprints at 28 pts. **Plan 8 sprints + 1 buffer sprint**, and cut
scope from the "stretch" list below rather than cutting tests or evaluation.

**Stretch / first to be cut:** 3.5 (LLM decomposer), 4.3 (Crossref), 8.7 (PDF export),
7.4 (correction self-check), 6.6 (adaptive budget → becomes future scope, and H2 is dropped
from the claimed contribution if so).

## Sprint plan

| Sprint | Theme | Main stories | Gate at end |
|---|---|---|---|
| 0 (3 days) | Phase 0 approval + repo | this doc set, ADR-001..006, 2.1, 2.3 | **contracts frozen v1**, CI skeleton green |
| 1 | Research + foundations | 1.1–1.5, 2.2, 2.4, 2.5, 9.1 | SRS + gap matrix approved |
| 2 | Extraction + retrieval core | 3.1–3.3, 4.1–4.2, 6.1 | claims extracted from real text; evidence returned |
| 3 | NLI + KG core | 3.4, 4.4, 5.1–5.2, 6.2 | Recall@5 measured; NLI scores per passage |
| 4 | Verification engine | 5.3–5.4, 6.3–6.4, 6.7, 7.1 | **end-to-end verdict with 6 statuses** (demo 1) |
| 5 | Mitigation + API + dataset | 7.2–7.5, 8.1–8.3, 10.1 | corrections with abstention; API live |
| 6 | Frontend + security | 8.4–8.6, 9.2–9.5, 5.5, 4.5 | dashboard demo; adversarial suite green |
| 7 | Evaluation | 10.2–10.5, 6.5, 6.6 | **real result tables** (demo 2) |
| 8 | Docs + hardening | 9.6, 10.6–10.9, 8.7 | report + synopsis draft; viva rehearsal |
| 9 (buffer) | Slip absorption | — | final submission |

Ceremonies: 20-min Monday planning, async daily standup in a GitHub Discussions thread,
Friday review (demo whatever exists) + 15-min retro written into `docs/agile/sprint-N.md`.
