# Contributing

Four people work on one codebase in parallel. These rules exist so that is possible.

## The one architectural rule

**Modules depend on `verifact.contracts`, never on each other.** `extraction` does not import
`retrieval`. The orchestrator passes contract objects between stages. If you find yourself
wanting to import a sibling module, you want a contract change instead — see below.

## Ownership

| Area | Primary | See |
|---|---|---|
| contracts, config, db, orchestrator, api, CI, Docker | **P1** Ankit | `team/p1-platform-api/` |
| input, extraction, mitigation, dashboard | **P2** Bhuvi | `team/p2-extraction-mitigation-ui/` |
| retrieval, source registry, knowledge graph | **P3** Ayush | `team/p3-retrieval-kg/` |
| verification, scoring, calibration, evaluation | **P4** Bhavish | `team/p4-verification-evaluation/` |

Full file-level matrix: `docs/phase-0/04-work-division.md §2`.

## Changing a contract

A contract change costs three other people a rebase, so it is deliberately expensive:

1. Open an issue labelled `type:task` describing what field you need and why.
2. PR against `src/verifact/contracts/` — **approved by P1 and by every affected owner**.
3. Add an entry to `src/verifact/contracts/CHANGELOG.md`.
4. **Regenerate the golden fixture you own in the same commit.** A shape change without a
   fixture update breaks everyone downstream silently.

## Golden fixtures

Handoffs between people are files, not live code, so nobody blocks on anybody:

| Fixture | Owned by | Consumed by |
|---|---|---|
| `tests/fixtures/claims_golden.json` | P2 | P3, P4 |
| `tests/fixtures/evidence_golden.json` | P3 | P4 |
| `tests/fixtures/kgcheck_golden.json` | P3 | P4 |
| `build/openapi.json` (CI artifact) | P1 | P2 |

If you consume a fixture, test against the fixture — not against the other person's module.

## Branches and commits

- Branch: `<type>/<issue>-<slug>`, e.g. `feat/42-bm25-retriever`.
- Conventional commits: `feat(retrieval): …`, `fix(kg): …`, `docs(arch): …`, `test(api): …`,
  `chore(ci): …`.
- Body says **why**, not what — the diff already says what.
- `Closes #NN` so the issue closes with the merge.
- Never commit directly to `main`.

## Before you open a PR

```bash
make check      # lint + types + tests + security. All of it, not some of it.
```

## Definition of Done

Full list in `docs/phase-0/03-agile-backlog.md`. The one people forget: **you must be able to
explain it out loud**, recorded as three bullets in your `team/<you>/explainer-log.md`. If you
cannot explain why the code exists, it does not ship.

## Things that will get a PR rejected

- A quality number (F1, Recall@k, ECE, latency) with no committed run behind it.
- A test that asserts a threshold we tuned until it passed.
- `except Exception: pass`, or any silently swallowed error.
- A hardcoded verdict, or a stub that returns a plausible-looking result.
- An API key, a credential, or a `.env` file.
- A new dependency or service without an ADR.
- `continue-on-error` in CI, or a skipped check presented as a green pipeline.
