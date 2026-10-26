# P3 — Evidence & Knowledge Graph Engineer

**Member:** <<TBD: name / roll no>>
**Epics:** 4 (Evidence Retrieval), 5 (Knowledge Graph), 9.5 (SSRF suite), 10.3 (Recall@k)

> Read `docs/phase-0/04-work-division.md` first. This file is the detail for one role.

## 1. Files you own (primary)

- `src/verifact/retrieval/registry.yaml` — the source registry and reliability tiers
- `src/verifact/retrieval/clients/` — Wikipedia/Wikidata, Crossref, local corpus; caching; SSRF guards
- `src/verifact/retrieval/{bm25,dense,fuse}.py` — BM25, FAISS, Reciprocal Rank Fusion
- `src/verifact/kg/` — entity linking, subgraph construction (NetworkX), triple mapping, consistency check
- `tests/security/test_ssrf.py`
- `docs/design/retrieval.md`, `docs/design/knowledge-graph.md`

## 2. What you consume from others

- `Claim` + `Entity` from P2 — code against `claims_golden.json`, **not** against P2's live module.
- `contracts` (P1): `EvidencePassage`, `Source`, `KGCheck`, `Triple`.

## 3. What others consume from you (your blocking deliverables)

- **`tests/fixtures/evidence_golden.json` and `kgcheck_golden.json`** (Wave 2) — unblocks P4's
  aggregation work entirely. Without these P4 is stuck behind flaky network calls.
- Reliability tiers that P4's weighting formula consumes — justify each tier in writing.
- Offline snapshot mode: the demo must work with the network off.

## 4. Your specific risks

- External APIs are the flakiest part of the system. Cache aggressively, record fixtures,
  and build the offline snapshot early (not in Wave 3 if you can help it).
- Entity linking ambiguity is the main correctness risk: "Washington" (person/state/city).
  An ambiguous mention must return candidates with confidences, never a silent pick.
- **KG incompleteness is not contradiction.** Wikidata missing a relation means `MISSING`.
  If your module ever returns `CONTRADICTED` for an absent fact, the whole system becomes a
  false-positive machine. Test this explicitly.
- SSRF: you are the only module making outbound requests. Allowlist, resolve-and-check IP,
  no off-allowlist redirects, timeout, response-size cap.

## 5. Your gate obligations

- Gate 1: ranked passages for a hand-written claim; first measured Recall@5.
- Gate 2: `evidence_golden.json` + `kgcheck_golden.json` merged; `KGCheck` distinguishes
  MISSING from CONTRADICTED.
- Gate 3: offline snapshot mode; staleness handling; SSRF suite green.
- Gate 4: Recall@k table for the report.

## 6. Your Definition of Done (in addition to the team DoD)

- Unit tests for your own logic — nobody else writes tests for your module.
- `docs/design/<your module>.md` updated in the same PR as the code.
- Three bullets in `explainer-log.md` per merged story.
- If you changed `contracts/`, the golden fixture you own is regenerated in the same commit.
- No number in your report sections that is not backed by a committed run.
