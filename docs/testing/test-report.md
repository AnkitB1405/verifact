# Test Report

**Date:** 2026-11-02 · **Commit:** end of Phase 7 · **Owner:** P1 (infrastructure), each owner for their own module

## What this report is and is not

Everything below under **Measured** was produced by running the suite on the
machine described, and the commands to reproduce it are given. Nothing here is a
quality metric for the *verification task* — no precision, recall, F1, AUROC,
ECE or Recall@k figure appears, because **Phases 8–12 have not been run.** The
evaluation harness, the baselines, the ablations and `verifact-stress` do not
exist yet.

That matters more than it might seem. A test report that quietly mixed "320
tests pass" with an invented F1 would be the exact failure the project is built
to detect. The decision thresholds in `config/` are **placeholders**; they have
not been fitted, and ADR-005's freeze protocol has not been executed.

---

## 1. Environment

| | |
|---|---|
| Python | 3.13 (CI matrix: 3.13) |
| OS | Linux, x86-64 |
| Hardware | CPU only, no GPU at any point |
| Transformer backends | `cross-encoder/nli-deberta-v3-small`, `sentence-transformers/all-MiniLM-L6-v2`, spaCy `en_core_web_sm` |
| Lexical backends | Jaccard similarity, heuristic NLI, BM25 — no model weights required |

## 2. Measured — suite results

```
pytest -m "not network"     320 passed, 10 deselected    13.4 s
pytest                      330 passed                   14.4 s
pytest --cov                85% line coverage on src/
```

The 70% coverage gate (NFR-07) passes with 15 points of headroom.

| Suite | Tests | What it covers |
|---|--:|---|
| `tests/unit/input` | 29 | offset invariant (property-based over 8 text shapes), validation, caps |
| `tests/unit/extraction` | 47 | the five ADR-002 worked examples, mentions, check-worthiness, golden fixture |
| `tests/unit/retrieval` | 29 | registry tiers, BM25/dense complementarity, RRF, determinism |
| `tests/unit/kg` | 35 | predicate map, comparison helpers, four KG statuses (live) |
| `tests/unit/verification` | 81 | all six statuses reachable, both invariants, weighting, calibration, explanation, budget |
| `tests/unit/mitigation` | 22 | abstention reasons, grounded substitution, annotation alignment |
| `tests/unit/test_logging.py` | 6 | redaction through the real handler |
| `tests/integration` | 12 | contract alignment, persistence round-trip, determinism, failure isolation |
| `tests/api` | 28 | six endpoints, auth, 429, typed errors, OpenAPI, dashboard |
| `tests/security` | 29 | 14 SSRF attacks, 9 prompt-injection attacks, structural LLM-free assertion |

### 2.1 Deselected tests, declared

10 tests carry the `network` marker and are **deselected in the default run and
in the main CI job**. They are not skipped silently: `-m "not network"` is in the
`Makefile` and in the workflow, and they run in the `ml` job on `main`. All 10
pass (the `pytest` line above is the full run).

They need live Wikidata and Wikipedia. Keeping them out of the default gate is
what makes CI deterministic; counting them as passing without running them would
be the "green pipeline that reflects skipped checks" the brief forbids.

### 2.2 Measured — latency, with its caveat

```
single-claim verification, lexical backend, offline, local corpus, n=20
p50 = 13.4 ms    p95 = 14.6 ms    min = 12.7 ms    max = 16.8 ms
```

**This number must not be quoted as evidence for NFR-01** (p50 ≤ 2.5 s). It is
the *cheap* path: no network, no transformer inference, no knowledge-graph
lookup. It establishes only that the pipeline's own orchestration overhead is
negligible — which is useful, because it means any latency we later measure on
the transformer path is model and network time, not our plumbing.

The NFR-01 and NFR-02 measurements require the transformer backend with warm
models and live sources, and belong to Phase 10.

## 3. Measured — static analysis and security tooling

| Check | Result |
|---|---|
| `ruff format --check src tests` | clean |
| `ruff check src tests` (E, F, I, UP, B, SIM, S, C4, RET, PTH) | 0 findings |
| `mypy` (strict, 55 source files) | 0 errors |
| `bandit -r src` | 0 low / 0 medium / 0 high |
| `alembic upgrade head → downgrade base → upgrade head` | clean, only `alembic_version` remains after downgrade (FR-63) |

`pip-audit`, `gitleaks` and the Trivy image scan are wired into CI
(`.github/workflows/ci.yml`) and have not been run locally for this report.

## 4. Measured — functional behaviour on real sources

Observed with the transformer backend against live Wikipedia and Wikidata, and
reproducible from the committed HTTP cache:

| Claim | Status | Decided by |
|---|---|---|
| The Eiffel Tower is located in Paris. | `SUPPORTED` | graph path, 2 hops via the 7th arrondissement |
| The Eiffel Tower is located in Berlin. | `CONTRADICTED` | knowledge graph |
| The Eiffel Tower was completed in 1889. | `SUPPORTED` | P1619, after EA-01 |
| The Eiffel Tower was completed in 1950. | `CONTRADICTED` | knowledge graph |
| The Eiffel Tower is 330 metres tall. | `SUPPORTED` | graph value +330 |
| My neighbour's cat is called Mitzi. | `UNVERIFIABLE` | similarity gate, after EA-07 |
| Marie Curie won the Nobel Prize in Physics in 1903. | `AMBIGUOUS` | graph confirms, text contradicts |
| Water boils at 100 degrees Celsius. | `NOT_APPLICABLE` (KG) | outside the predicate set |

Grounded corrections produced, each citing Wikidata:
`completed in 1950 → 1889`, `is 500 metres tall → 324 metres`. `SUPPORTED` and
`UNVERIFIABLE` claims abstain.

**One of these is wrong and is reported as wrong:** the Marie Curie claim is
true, and `AMBIGUOUS` is not the right answer. It is an improvement on the
`CONTRADICTED` it returned before the KG-support fix, and the residual cause —
the NLI model scoring irrelevant passages as contradictions — is EA-05.

## 5. Defects found and fixed during development

Eleven, written up in `error-analysis.md` as they happened. Six changed
behaviour the project depends on:

| id | Defect | Why it mattered |
|---|---|---|
| EA-01 | `completed in` mapped to Wikidata P571 (inception, 1887) rather than P1619 (opening, 1889) | false `CONTRADICTED` on a true claim from a tier-1 source, with a confident explanation |
| EA-05 | NLI gives contradiction ≈1.0 for irrelevant passages | open; contained by relevance weighting and the similarity gate, not eliminated |
| EA-07 | min-max relevance meant coverage could never report "nothing relevant found" | every claim looked covered; `UNVERIFIABLE` was unreachable in practice |
| EA-09 | one similarity threshold for two different similarity measures | the lexical backend — the one CI runs — marked everything `UNVERIFIABLE` |
| EA-10 | a negation anywhere in a passage flipped the lexical verdict | content injection: one appended sentence could flip a verdict, no model involved |
| EA-11 | `LoggerAdapter.process` replaced call-site `extra` | every structured log field was discarded and the redaction filter had nothing to redact, while its own unit test passed |

EA-08 remains **open and deliberately unfixed**: a fabricated entity returns
`CONTRADICTED` where `UNVERIFIABLE` would be honest. Closing it by raising
`tau_sim` would be fitting a threshold to one hand-picked example, which ADR-005
forbids.

## 6. Requirements coverage

63 functional requirements, each naming a test in the SRS. Not satisfied at this
commit, and therefore listed in Known Limitations rather than quietly dropped:

| id | Requirement | State |
|---|---|---|
| FR-12 | optional LLM decomposer | not implemented; rules-only path ships (ADR-002) |
| FR-41 | re-verify a generated correction | not implemented; substitution-based correction makes it less critical, but it is still a gap |
| FR-60 | KG subgraph visualisation | API returns the path; the dashboard renders it as text, not a graph |
| NFR-01/02 | latency targets | not measured on the transformer path |
| NFR-03 | 4 GB memory ceiling | not measured |
| NFR-13 | 30-minute install from docs alone | not attempted by anyone who did not write the docs |
| NFR-14 | ECE reported | the machinery and its unit tests exist; no ECE has been measured on real data |

## 7. How to reproduce

```bash
make install            # core + dev, no model weights
make test               # 320 tests, no network, no models
make cov                # with the 70% gate
make lint types sec     # ruff, mypy, bandit, pip-audit

make install-ml         # transformer backends + spaCy model (~2 GB)
make test-all           # all 330, including live-source tests
```

The `ml`-marked tests require network access on first run to download model
weights, and live Wikipedia/Wikidata access for the `network`-marked ones.
