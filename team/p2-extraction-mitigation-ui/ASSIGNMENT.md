# P2 — NLP Input, Mitigation & Frontend Engineer

**Member:** <<TBD: name / roll no>>
**Epics:** 3 (Claim Extraction), 7 (Mitigation, Explainability rendering), 8 (Frontend), 9.5 (prompt-injection suite)

> Read `docs/phase-0/04-work-division.md` first. This file is the detail for one role.

## 1. Files you own (primary)

- `src/verifact/input/` — validation, normalisation, sentence splitting with char offsets
- `src/verifact/extraction/` — entities, dates, numbers, atomic claim decomposition, check-worthiness
- `src/verifact/mitigation/` — corrector, abstention policy, annotated-text renderer
- `frontend/**` (React + TS + Vite + Tailwind), `frontend/src/api/client.ts` (generated)
- `tests/security/test_prompt_injection.py`
- `docs/user-guide/`

## 2. What you consume from others

- `contracts` (P1). If `Claim` lacks a field you need, PR it **in Wave 0**.
- `Verdict` + evidence (P4/P3) for corrections — you only *use* scores, you never invent them.
- OpenAPI artifact (P1) → regenerate `client.ts`; never hand-write response types.

## 3. What others consume from you (your blocking deliverables)

- **`tests/fixtures/claims_golden.json`** (Wave 1) — unblocks P3 and P4. Highest-priority deliverable.
- `Correction` objects with citations and honest abstention.
- The dashboard, which is what the panel will actually look at.

## 4. Your specific risks

- Breadth: NLP + UI is two different skill sets. Do the NLP first; the UI can be built fast
  in Wave 3 once the API is stable. Do not start the UI before Gate 2.
- "Atomic claim" has no universal definition. Write yours down in `module-design.md` with
  5 worked examples **before coding**, and get P4 to agree, because P4's metrics depend on it.
- Correction is where fabrication sneaks in. Your corrector must cite evidence it is entailed
  by, and must abstain rather than guess. Enforce this with a test, not with discipline.

## 5. Your gate obligations

- Gate 1: `claims_golden.json` merged; offsets round-trip exactly.
- Gate 2: check-worthiness filter measured on a labelled set; corrector drafted on fixtures.
- Gate 3: dashboard end-to-end; abstention working; injection suite green.
- Gate 4: export + user manual.

## 6. Your Definition of Done (in addition to the team DoD)

- Unit tests for your own logic — nobody else writes tests for your module.
- `docs/design/<your module>.md` updated in the same PR as the code.
- Three bullets in `explainer-log.md` per merged story.
- If you changed `contracts/`, the golden fixture you own is regenerated in the same commit.
- No number in your report sections that is not backed by a committed run.
