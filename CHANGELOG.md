# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: SemVer.

## [Unreleased]

### Added
- Phase 0: project initiation, research plan, preliminary architecture, agile backlog, four-person work division.
- Phase 1: 30 paper records with API-verified metadata, gap matrix, novelty statement, ADR-001.
- Phase 2: SRS (63 FR, 15 NFR, 8 SR); the six verification statuses frozen.
- Phase 3: system architecture v1.0 with Mermaid C4/sequence/ER diagrams; ADR-002 … ADR-007.
- Phase 5: project skeleton, shared contracts, configuration, structured logging with
  redaction, error taxonomy, ORM models, first Alembic migration, Dockerfile, compose,
  CI pipeline (lint, types, tests+coverage gate, migrations up/down, bandit, pip-audit,
  gitleaks, Trivy, image healthcheck), issue and PR templates.

### Changed
- Frontend decision reversed: React + Vite replaced by a static dashboard (ADR-007).
- Queue decision settled: FastAPI background tasks instead of Celery + Redis (ADR-004).

- Phase 6: input processing, claim extraction, evidence retrieval, knowledge-graph
  verification, the five-stage verification engine, calibration, adaptive budget,
  explanation assembly, grounded correction with abstention, orchestrator, six REST
  endpoints, and the dashboard.
- Phase 7: 330 tests (320 offline), 85% coverage, SSRF and prompt-injection suites,
  integration and API suites.
- `docs/testing/error-analysis.md`: 11 defects found during development, with causes.
- `docs/testing/test-report.md`: measured results only.

### Fixed
- Aggregation ignored a `SUPPORTED` knowledge-graph result, producing a false
  `CONTRADICTED` on a true claim (EA-05 fallout).
- Evidence coverage could never report "nothing relevant retrieved", because relevance is
  min-max scaled per claim (EA-07).
- A single similarity threshold was applied to two incomparable similarity measures, so the
  lexical backend marked every claim `UNVERIFIABLE` (EA-09).
- A negation anywhere in a passage flipped the lexical verdict — a content-injection
  vulnerability found by the prompt-injection suite (EA-10).
- `LoggerAdapter.process` replaced call-site `extra`, discarding every structured log field
  and leaving the redaction filter with nothing to redact (EA-11).
- Verdict confidence described the text margin even when the knowledge graph had decided the
  verdict.

### Known gaps at this point
- Phase 4 (GitHub issues, epics, board) deliberately skipped; the backlog lives in
  `docs/phase-0/03-agile-backlog.md` only.
- **No measured quality numbers.** No precision, recall, F1, AUROC, ECE or Recall@k figure
  exists. Every NFR target is a target. Decision thresholds are placeholders and ADR-005's
  freeze protocol has not been executed.
- EA-08 open: a fabricated entity returns `CONTRADICTED` where `UNVERIFIABLE` would be
  honest. Not closed by tuning a threshold, on purpose.
- FR-12 (LLM decomposer), FR-41 (correction re-verification) and FR-60 (graph visualisation)
  are not implemented.
