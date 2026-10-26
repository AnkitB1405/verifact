# P1 — Platform, API & Release Engineer

**Member:** <<TBD: name / roll no>>
**Epics:** 2 (Architecture & Data Model), 8 (API half), 9 (Testing & Security infra), 10.6–10.7 (CI/CD, deployment docs)

> Read `docs/phase-0/04-work-division.md` first. This file is the detail for one role.

## 1. Files you own (primary)

- `contracts/*.py`, `contracts/CHANGELOG.md`  ← **you are the gatekeeper of the shared data model**
- `src/verifact/config.py`, `logging.py`, `errors.py`, `deps.py`
- `src/verifact/db/models.py`, `alembic/` migrations
- `src/verifact/orchestrator/pipeline.py`
- `src/verifact/api/v1/{analyze,verify,correct,results,feedback,health}.py`, auth + rate limiting
- `Dockerfile`, `compose.yaml`, `Makefile`, `.github/workflows/*`, `.pre-commit-config.yaml`
- `tests/integration/`, `tests/api/`, coverage gate
- `docs/architecture/`, `docs/deployment/`, `docs/security/`, SRS

## 2. What you consume from others

- `Verdict`, `Correction`, `AnalysisRun` produced by P4 and P2 — you only serialise them, you never compute scores.
- Stage order of the pipeline: proposed by P4, implemented by you.

## 3. What others consume from you (your blocking deliverables)

- **`contracts v1`** (Wave 0) — blocks P2, P3, P4. Ship it first, ship it early, then freeze it.
- **OpenAPI JSON artifact** on every merge to `main` — P2 generates the frontend client from it.
- `docker compose up` working at all times — this is the demo machine.

## 4. Your specific risks

- You are on the critical path twice (contracts, then orchestrator+API). Do not take on
  research or UI work.
- Biggest failure mode: letting contracts drift after Gate 0. Every change costs three other
  people a rebase. Require a `contracts/CHANGELOG.md` entry + fixture regeneration in the
  same PR, including your own PRs.
- Second failure mode: a CI pipeline that is green because checks are skipped or
  `continue-on-error`. That is a marking failure. No masking.

## 5. Your gate obligations

- Gate 0: contracts v1 tagged, CI green, `/health` 200 in Docker.
- Gate 2: orchestrator produces a persisted `AnalysisRun`.
- Gate 3: all six endpoints live, authed, rate-limited, documented in OpenAPI.
- Gate 4: integration+API tests, coverage gate, 4 security scanners wired, latency measured.

## 6. Your Definition of Done (in addition to the team DoD)

- Unit tests for your own logic — nobody else writes tests for your module.
- `docs/design/<your module>.md` updated in the same PR as the code.
- Three bullets in `explainer-log.md` per merged story.
- If you changed `contracts/`, the golden fixture you own is regenerated in the same commit.
- No number in your report sections that is not backed by a committed run.
