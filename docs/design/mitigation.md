# Correction and Mitigation

**Owner:** P2 (Bhuvi) · **Code:** `src/verifact/mitigation/` · **Requirements:** FR-37…FR-42
**Produces:** `Correction`, annotated text

## What it does

Proposes an evidence-grounded correction for a claim the system found wrong, or
**abstains**. Also renders the original text with problem spans marked.

## Why it exists

Detection alone leaves the reader with "this is wrong" and no idea what is right.
But a wrong correction is worse than none: it launders a fabrication into
something that now carries a citation.

So the module is built around abstention being a *first-class, common* outcome
rather than a failure path.

## How it works internally

**No language model generates a correction.** A correction is a *substitution* of
a value taken from a cited passage or a knowledge-graph statement into the
original claim text.

That is an architectural choice, not a shortcut:

- **FR-39 — "introduce no unsupported claim" — becomes true by construction.**
  Only one span changes, and the replacement came from something cited. A
  generative reviser can only *promise* this; RARR's own framing is that its LLM
  reviser may introduce new content.
- The output is reproducible (NFR-06).
- There is **no prompt to inject**. Retrieved text is never an instruction, only
  a source of a value.

Order of attempts: the knowledge-graph note first (it already reports what the
graph holds, so no second lookup is needed), then a cited contradicting passage.
Only values of the *same kind* are considered — a year may replace a year, a
number a number — because any broader edit would be the module writing prose.

It abstains when: the status is not `CONTRADICTED` or `OUTDATED`; the evidence
confidence is below threshold; no replacement of the right kind exists; or the
value to replace cannot be located in the claim text. Every abstention records
its reason.

`max_supportable_confidence` caps the correction at the confidence of the
evidence behind it (FR-40).

**Annotation** applies markers right-to-left so an earlier insertion never shifts
a later offset, and only the first span at a given start position is marked so
overlapping claims from one sentence do not nest markers. `SUPPORTED` is not
marked inline — marking everything is the same as marking nothing.

## What alternatives exist

| Alternative | Why not |
|---|---|
| LLM rewriting (RARR, CoVe) | more capable, and it can introduce new unsupported content, cannot be reproduced, and reintroduces an injection surface |
| Template-based rewriting | more fluent output, but a template per relation type and no gain in groundedness |
| Always correct, never abstain | RARR's posture; a system that always revises will sometimes revise a correct claim into an incorrect one |
| Delete the unsupported span | destroys meaning and is not what a reader wants |

## What could go wrong

- **Structurally wrong claims cannot be fixed.** Only a wrong number, date or
  entity is substitutable. Everything else abstains — honest, and a real
  capability limit.
- **It abstains most of the time**, which looks like the module doing nothing. It
  is the module working.
- **The graph's first value may not be the best one.** For a property with
  several values — the Eiffel Tower is 300, 324 or 330 m depending on the antenna
  — the correction picks the first, so "500 metres" became "324 metres" rather
  than 330.
- **FR-41 (re-verify the generated correction) is not implemented.**
  Substitution makes it less critical than it would be for a generative
  corrector, but it remains a gap and is listed in the test report.
- **A correction inherits the verdict's errors.** If the verdict is a false
  `CONTRADICTED`, the correction confidently "fixes" a true claim.

## How it is tested

22 tests. Abstention is tested per reason, not just per outcome. Correction tests
assert a citation is always present, that the confidence ceiling is recorded,
that only the substituted span changes, and that output is deterministic.
Annotation tests assert that stripping the markers reproduces the original text
exactly — the offset invariant, checked at the far end of the pipeline.

Two tests live in the injection suite: an instruction embedded in a passage
cannot force a correction, and a value injected into prose cannot be substituted,
because the corrector reads graph values from the KG stage's structured note and
an attacker controlling passage text cannot reach that channel.
