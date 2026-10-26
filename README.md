# VeriFact — Phase 0 (Initiation)

> An explainable AI hallucination **detection and mitigation** framework using trusted sources
> and knowledge graphs.
> **Status: Phase 0. No implementation code has been written.** Awaiting approval of the
> architecture and the novelty claim before Phase 1.

## Read in this order

| # | Document | What it decides |
|---|---|---|
| 1 | [`docs/phase-0/00-project-initiation.md`](docs/phase-0/00-project-initiation.md) | scope, the 6 hard constraints, **missing information** |
| 2 | [`docs/phase-0/01-research-plan.md`](docs/phase-0/01-research-plan.md) | how the survey is done, H1/H2, baselines, datasets |
| 3 | [`docs/phase-0/02-preliminary-architecture.md`](docs/phase-0/02-preliminary-architecture.md) | modules, contracts, aggregation maths, tech choices, ADRs to approve |
| 4 | [`docs/phase-0/03-agile-backlog.md`](docs/phase-0/03-agile-backlog.md) | 10 epics, ~50 stories, 9-sprint plan, DoD |
| 5 | [`docs/phase-0/04-work-division.md`](docs/phase-0/04-work-division.md) | **the 4-person split, ownership matrix, contribution sequence** |

Then each member reads only their own `team/<role>/ASSIGNMENT.md`.

## The team split in one table

| | Role | Blocking deliverable (ships first) |
|---|---|---|
| P1 | Platform, API & Release | `contracts/` v1 + CI + `/health` — Wave 0 |
| P2 | Input, Extraction, Mitigation, UI | `tests/fixtures/claims_golden.json` — Wave 1 |
| P3 | Evidence Retrieval & Knowledge Graph | `evidence_golden.json` + `kgcheck_golden.json` — Wave 2 |
| P4 | Verification, Scoring & Research | 6-status rule + every measured number — Waves 0, 2, 4 |

Handoffs are **golden fixture files**, so nobody waits on anybody's live code.

## What must happen before Phase 1 starts

1. Supply the 10 missing items in `00-project-initiation.md §5` (templates, names, compute, deadlines).
2. Approve or reject ADR-001 … ADR-006 (listed in `02-preliminary-architecture.md §6`).
3. Assign P1–P4 to real people.

## Non-negotiables carried into every phase

- Absence of evidence is never a verdict of false.
- No fabricated citations, results, or test outcomes — measured, preliminary, expected and
  proposed results are reported in separate sections.
- Component scores are always shown alongside the aggregate.
- Retrieved evidence is data, never instruction.
- Nothing is Done without a passing test, a tracked issue, and an owner who can explain it.
