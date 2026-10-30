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

### Known gaps at this point
- Phase 4 (GitHub issues, epics, board) deliberately skipped; the backlog lives in
  `docs/phase-0/03-agile-backlog.md` only.
- No measured quality numbers yet. Every NFR target is a target, not a result.
