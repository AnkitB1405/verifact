# VeriFact

> An explainable AI hallucination **detection and mitigation** framework using trusted sources
> and knowledge graphs.
>
> **It reports whether each claim is attributable to a configured set of trusted sources.
> It does not determine truth.** A claim it cannot verify is `UNVERIFIABLE` — meaning no
> source covering it was found, not that it is false.

**Status: phases 0–3 and 5–7 complete** (phase 4, the GitHub issue/board setup, was skipped).
Working pipeline, REST API, dashboard, 330 tests, 85% coverage. **No evaluation has been run
yet**: there are no precision, recall, F1, AUROC or ECE figures anywhere in this repository,
and the decision thresholds in `config/` are placeholders. That work is phases 8–12.

## Quick start

```bash
make install        # core deps, no model weights needed
make migrate
make dev            # http://127.0.0.1:8000  — dashboard and /docs
make test           # 320 tests, no network, no models

make install-ml     # transformer backends + spaCy model, ~2 GB
make test-all       # all 330, including live Wikipedia/Wikidata tests
```

Without the `ml` extra the pipeline runs on lexical backends: BM25 retrieval,
token-overlap similarity and a heuristic NLI. Quality is materially lower and every run
records which backend produced it, so a degraded result is visible rather than silent.

## What it does, on one claim

```
$ curl -s localhost:8000/api/v1/verify -H 'Content-Type: application/json' \
    -d '{"claim":"The Eiffel Tower was completed in 1950."}' | jq -r .explanation

CONTRADICTED: trusted sources contradict this statement.
Reason: the knowledge graph holds a conflicting value: claim says 1950, graph holds ['1889']
Confidence: uncalibrated score 0.90 (not a probability).
Evidence: 0 supporting, 2 contradicting, coverage 0.26, agreement across sources 0.00.
Knowledge graph: CONTRADICTED. The Eiffel Tower: claim says 1950, graph holds ['1889']
```

## The six verdicts

`SUPPORTED` · `CONTRADICTED` · `UNVERIFIABLE` · `INSUFFICIENT_EVIDENCE` · `OUTDATED` ·
`AMBIGUOUS` — defined with worked examples in
[`docs/requirements/verification-statuses.md`](docs/requirements/verification-statuses.md).

The distinction the whole system is built around: **absence of evidence is never reported as
falsehood.**

## Documentation

| # | Document | What it decides |
|---|---|---|
| 1 | [`docs/phase-0/00-project-initiation.md`](docs/phase-0/00-project-initiation.md) | scope, the 6 hard constraints, **missing information** |
| 2 | [`docs/phase-0/01-research-plan.md`](docs/phase-0/01-research-plan.md) | how the survey is done, H1/H2, baselines, datasets |
| 3 | [`docs/phase-0/02-preliminary-architecture.md`](docs/phase-0/02-preliminary-architecture.md) | modules, contracts, aggregation maths, tech choices, ADRs to approve |
| 4 | [`docs/phase-0/03-agile-backlog.md`](docs/phase-0/03-agile-backlog.md) | 10 epics, ~50 stories, 9-sprint plan, DoD |
| 5 | [`docs/phase-0/04-work-division.md`](docs/phase-0/04-work-division.md) | **the 4-person split, ownership matrix, contribution sequence** |

| 6 | [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md) | C4, sequence and ER diagrams; the aggregation formula and status rule |
| 7 | [`docs/requirements/SRS.md`](docs/requirements/SRS.md) | 63 FR, 15 NFR, 8 SR, each naming its test |
| 8 | [`docs/testing/error-analysis.md`](docs/testing/error-analysis.md) | **11 real defects found while building, with the lesson from each** |
| 9 | [`docs/testing/test-report.md`](docs/testing/test-report.md) | measured results, and what is explicitly not measured |
| 10 | [`docs/architecture/decisions/`](docs/architecture/decisions/) | ADR-002 … ADR-007, each with its migration trigger |

Then each member reads only their own `team/<role>/ASSIGNMENT.md`.

If you read one document, read `error-analysis.md`. It is where the project's reasoning is
most visible: six of the eleven entries changed behaviour the system depends on, and one
(EA-08) is deliberately left open rather than closed by moving a threshold.

## The team split in one table

| | Role | Blocking deliverable (ships first) |
|---|---|---|
| P1 | Platform, API & Release | `contracts/` v1 + CI + `/health` — Wave 0 |
| P2 | Input, Extraction, Mitigation, UI | `tests/fixtures/claims_golden.json` — Wave 1 |
| P3 | Evidence Retrieval & Knowledge Graph | `evidence_golden.json` + `kgcheck_golden.json` — Wave 2 |
| P4 | Verification, Scoring & Research | 6-status rule + every measured number — Waves 0, 2, 4 |

Handoffs are **golden fixture files**, so nobody waits on anybody's live code.

## What is still outstanding

1. The 10 missing items in `00-project-initiation.md §5` — synopsis and report templates,
   university details, deadlines. Placeholders are greppable as `<<TBD`.
2. Phases 8–12: integration hardening, CI/CD on a real runner, the evaluation
   (baselines A–D, ablations, `verifact-stress`), full documentation, synopsis and report.
3. ADR-001's novelty claim needs guide sign-off, and the targeted literature search named
   in `gap-matrix.md` (threat 2) must be run before the report is written — even if it
   weakens the claim.
4. Every paper record carries `full_text_read_by: <<TBD>>`. The records were written from
   published abstracts with API-verified metadata; the full reads are a real task.

## Non-negotiables carried into every phase

- Absence of evidence is never a verdict of false.
- No fabricated citations, results, or test outcomes — measured, preliminary, expected and
  proposed results are reported in separate sections.
- Component scores are always shown alongside the aggregate.
- Retrieved evidence is data, never instruction.
- Nothing is Done without a passing test, a tracked issue, and an owner who can explain it.
