# Contract changelog

Every change to `models.py` gets an entry. Three other modules are built against these
types; an undocumented shape change is how four parallel streams break silently.

## v1 — 2026-10-30 — initial freeze (P1)

Models: `Document`, `Sentence`, `Claim`, `Entity`, `TemporalRef`, `NumericRef`, `Source`,
`RetrievalScores`, `EvidencePassage`, `Triple`, `KGCheck`, `ComponentScores`, `Verdict`,
`Citation`, `Correction`, `RunProvenance`, `AnalysisRun`.
Enums: `VerdictStatus` (6), `KGStatus` (4), `SourceKind`, `RunStatus`, `ClaimType`.

Invariants enforced in the models themselves, not by convention:

- `Sentence.char_end > char_start`.
- `Correction`: abstained ⟹ no `corrected_text` **and** a reason; not abstained ⟹ text
  **and** at least one citation (FR-37, FR-38).
- `Verdict.calibrated` defaults to `False`; only `verification.calibrate` sets it `True`
  (ADR-005).
- `KGStatus.MISSING` exists specifically so an absent relation is distinguishable from a
  contradicted one (FR-24).
- All models are frozen with `extra="forbid"`: a typo in a field name is an error, not a
  silently ignored attribute.
