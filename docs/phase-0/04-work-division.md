# Four-Person Work Division, Co-ownership Rules, and Contribution Sequence

> This was **not** specified in the brief, so it is defined here.
> Names are `<<TBD: team member names>>`; roles are P1–P4 until assigned.

## 0. The two rules that make this work

**Rule A — vertical slices, not file silos.** Each person owns a *capability* end-to-end:
its module code, its unit tests, its design doc, its report chapter, its viva answers. Nobody
is "the tester" or "the documenter"; everyone tests and documents their own slice.

**Rule B — interdependent files have a primary and a secondary, and a declared direction.**
Where two slices meet, the file has one **primary owner** (merges, decides) and one or more
**secondary contributors** (open PRs against it). The dependency direction is always toward
`contracts/`: modules depend on the contracts, never on each other's internals. A contract
change is a PR that both owners approve, plus an entry in `contracts/CHANGELOG.md`.

---

## 1. Roles

| | Role | Owns (capability) | Epics |
|---|---|---|---|
| **P1** | Platform, API & Release Engineer | contracts, config, DB+migrations, orchestrator, FastAPI, auth/rate-limit, logging, error handling, Docker, CI/CD, security tooling | 2, 8 (API), 9, 10 (deploy/CI) |
| **P2** | NLP Input, Mitigation & Frontend Engineer | input processing, claim extraction, check-worthiness, correction + abstention, annotated text, dashboard | 3, 7 (mitigation), 8 (UI) |
| **P3** | Evidence & Knowledge Graph Engineer | source registry, source clients + SSRF guards, BM25/FAISS/RRF retrieval, entity linking, KG build + consistency check | 4, 5 |
| **P4** | Verification, Scoring & Research Engineer | similarity, NLI, reliability/recency weighting, aggregation + 6 statuses, calibration, adaptive budget, explanation, baselines, evaluation, literature review | 1, 6, 7 (scoring), 10 (eval) |

Load is deliberately uneven per *epic count* and even per *difficulty*: P4 carries the
research risk, P1 carries the integration risk, P3 carries the external-API risk, P2 carries
the breadth (NLP + UI). Reassign P2↔P3 if one member is much stronger at frontend.

Cross-cutting duties everyone has: reviewing PRs (every PR needs one non-author approval),
writing ≥4 paper records, writing ≥30 items of `verifact-stress`, ≈13 viva Q&As,
and one retro entry per sprint.

---

## 2. File ownership matrix

`P` = primary (merges), `s` = secondary (contributes via PR), `r` = reviewer required.

| Path | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| `contracts/*.py`, `contracts/CHANGELOG.md` | **P** | s | s | s |
| `src/verifact/config.py` (sections per module) | **P** | s | s | s |
| `src/verifact/logging.py`, `errors.py`, `deps.py` | **P** | | | |
| `src/verifact/db/models.py`, `migrations/` | **P** | | | s (eval tables) |
| `src/verifact/orchestrator/pipeline.py` | **P** | s | s | **s (stage order)** |
| `src/verifact/orchestrator/budget_policy.py` | s | | | **P** |
| `src/verifact/api/v1/*.py` | **P** | s (correct/feedback shapes) | | s (verify shape) |
| `src/verifact/input/*.py` | r | **P** | | |
| `src/verifact/extraction/*.py` | | **P** | s (entity→KB id handoff) | |
| `src/verifact/retrieval/registry.yaml` | | | **P** | **s (weights)** |
| `src/verifact/retrieval/*.py`, `clients/*.py` | r (SSRF review) | | **P** | s |
| `src/verifact/kg/*.py` | | | **P** | s (consumes `KGCheck`) |
| `src/verifact/verification/{similarity,nli,aggregate,calibrate}.py` | | | | **P** |
| `src/verifact/verification/engine.py` | s | | s (kg adapter) | **P** |
| `src/verifact/explain/assembler.py` | | s (render) | | **P** |
| `src/verifact/mitigation/*.py` | | **P** | | **s (re-verify hook)** |
| `frontend/src/api/client.ts` (generated from OpenAPI) | **s (generator)** | **P** | | |
| `frontend/**` | | **P** | | s (score panel spec) |
| `eval/harness.py`, `eval/baselines/*.py` | s | | s (Recall@k) | **P** |
| `eval/datasets/verifact_stress/*.jsonl` | s | s | s | **P** |
| `tests/unit/<module>/` | own | own | own | own |
| `tests/integration/`, `tests/api/` | **P** | s | s | s |
| `tests/security/` | s | **P** (injection) | **P** (SSRF) | |
| `.github/workflows/*`, `Dockerfile*`, `compose.yaml`, `Makefile` | **P** | | | |
| `docs/architecture/`, `docs/deployment/`, `docs/security/` | **P** | s | s | s |
| `docs/research/`, `docs/testing/test-report.md` (results) | | | | **P** |
| `docs/design/<module>.md` | own | own | own | own |
| `docs/user-guide/` | s | **P** | | |

### The three genuinely hard interfaces (where things will break)

1. **`Claim` ⟶ retrieval & KG (P2 → P3).** P3 needs `entities[].surface` and spans to build
   queries and link to QIDs. *Protocol:* P2 ships `Claim` + a frozen fixture file
   `tests/fixtures/claims_golden.json` in Sprint 2; P3 codes against the fixture, not against
   P2's live code. Any change to `Claim` regenerates the fixture in the same PR.
2. **Evidence + `KGCheck` ⟶ verification (P3 → P4).** *Protocol:* P3 ships
   `tests/fixtures/evidence_golden.json` and `kgcheck_golden.json` in Sprint 3. P4's
   aggregation tests use only fixtures, so P4 is never blocked by a flaky external API.
3. **`Verdict`/`Correction` ⟶ API ⟶ UI (P4/P2 → P1 → P2).** *Protocol:* P1 publishes the
   OpenAPI JSON on every merge to `main` as a CI artifact; P2 regenerates
   `frontend/src/api/client.ts` from it. The UI never hand-writes response types.

**Golden-fixture rule:** the producer of a contract owns its fixture, and a PR that changes
the shape must update the fixture in the same commit. This is how four people work in
parallel without waiting on each other.

---

## 3. Contribution sequence

Within a wave, the listed work is parallel. A wave starts only when the previous wave's
**gate** is met. Each entry is `owner: what they land`.

### Wave 0 — Foundations (Sprint 0, ~3 days) — *everything else depends on this*
1. **P1**: repo skeleton, `pyproject.toml`, `config.py`, `logging.py`, `errors.py`,
   `contracts/*.py` **v1**, CI skeleton (ruff+mypy+pytest), `compose.yaml`, `/health`.
2. **P4** (parallel): ADR-001 novelty statement draft; freezes the 6 status definitions —
   P1 encodes them as an enum in `contracts/`.
3. **P2, P3** (parallel): review and PR against `contracts/` for fields their modules need —
   **this is the moment to add fields; later changes are expensive.**
> **Gate 0:** `contracts v1` tagged, CI green, `docker compose up` serves `/health`.

### Wave 1 — Producers (Sprint 1–2)
4. **P1**: DB models + Alembic migration; SRS; architecture doc with real diagrams.
5. **P2**: `input/` then `extraction/` (sentences → entities → atomic claims) → **ships
   `claims_golden.json`**.
6. **P3**: `registry.yaml` + source clients + SSRF guards (does *not* need P2 yet — codes
   against hand-written claims), then BM25+FAISS+RRF.
7. **P4**: literature review + gap matrix; `similarity.py` and `nli.py` against hand-written
   (claim, passage) pairs.
> **Gate 1:** `claims_golden.json` merged; retrieval returns ranked passages for a hand-written
> claim; NLI returns 3-way probs. Recall@5 has a first measured number.

### Wave 2 — Consumers (Sprint 3–4)
8. **P3**: entity linking → subgraph → `kg/consistency.py` → **ships `evidence_golden.json`
   + `kgcheck_golden.json`**.
9. **P4**: `aggregate.py` (weighting + 6-status rule) + `explain/assembler.py`, tested purely
   on P3's fixtures → then `verification/engine.py`.
10. **P1**: `orchestrator/pipeline.py` wiring input→extraction→retrieval→engine; persists
    `AnalysisRun`. **P4 reviews stage order.**
11. **P2** (parallel): check-worthiness filter; starts `mitigation/corrector.py` against
    fixture verdicts.
> **Gate 2 (Demo 1):** one CLI/REST call on a real 5-sentence paragraph returns per-claim
> verdicts in all six statuses across a test set, with component scores. **No UI yet.**

### Wave 3 — Surface (Sprint 5–6)
12. **P1**: all six endpoints + versioning + auth + rate limit + error schema;
    publishes OpenAPI artifact.
13. **P2**: correction + abstention + correction re-verify (hook reviewed by **P4**) +
    annotated-text renderer; then regenerates `client.ts` and builds the dashboard
    (input → claims → evidence inspector → score panel → diff view).
14. **P3**: offline snapshot mode, KG staleness handling, SSRF test suite.
15. **P4**: calibration + ECE; adaptive budget policy; `explain` strings finalised.
16. **All**: write 30 `verifact-stress` items each; cross-review (nobody labels their own).
> **Gate 3 (Demo 2):** dashboard runs the full pipeline end-to-end; adversarial
> injection/SSRF suite green in CI; `verifact-stress` v1 complete and reviewed.

### Wave 4 — Evidence of quality (Sprint 7)
17. **P4**: baselines A/B/C; evaluation harness; main result tables; ablations; error analysis.
18. **P3**: Recall@k numbers feeding the retrieval section.
19. **P1**: integration + API tests, coverage gate, bandit/pip-audit/gitleaks/Trivy,
    latency/throughput measurement.
20. **P2**: UI polish, export, user manual.
> **Gate 4:** every table in the report has a committed run artifact behind it. Any number we
> could not measure is moved to an *Expected / Future* section and labelled.

### Wave 5 — Deliverables (Sprint 8 + buffer)
21. **P1**: deployment guide, install guide, CI docs, release tag `v1.0.0`, changelog.
22. **P4**: literature review chapter, methodology chapter, results chapter, limitations.
23. **P2**: user manual, UI chapter, mitigation chapter.
24. **P3**: retrieval + KG chapters.
25. **All**: synopsis assembly, report assembly against the supplied templates
    `<<TBD: templates>>`, 50 viva Q&As (≈13 each), demo script, rehearsal where **each
    person is quizzed on someone else's module** — gaps there are the real audit.

### Critical path (what delays everything if late)
`contracts v1 (P1)` → `claims_golden (P2)` → `evidence/kgcheck_golden (P3)` →
`aggregate+engine (P4)` → `orchestrator (P1)` → `API (P1)` → `UI (P2)` → `eval (P4)`.
Four of the five handoffs are **fixture files**, so the slack is in code, not in people.

---

## 4. Per-person folders

`team/p1-platform-api/`, `team/p2-extraction-mitigation-ui/`, `team/p3-retrieval-kg/`,
`team/p4-verification-evaluation/`

Each contains:

| File | Purpose |
|---|---|
| `ASSIGNMENT.md` | the person's scope, files owned, interfaces in/out, gates, DoD |
| `module-design.md` | their design doc, filled during their waves (headings pre-set) |
| `test-plan.md` | what they test and how, incl. their adversarial cases |
| `report-sections.md` | exactly which synopsis/report chapters they write |
| `viva-questions.md` | their ≈13 Q&As, answered in their own words |
| `explainer-log.md` | 3 bullets per merged story — the DoD "can explain it" artifact |

These folders hold **planning and accountability artifacts only**. Production code lives in the
single shared tree (`src/`, `frontend/`, `eval/`, `tests/`) — splitting the codebase by person
would make the integration in Wave 2–3 impossible.
