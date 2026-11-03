# Explainability

**Owner:** P4 (Bhavish) · **Code:** `src/verifact/explain/` · **Requirements:** FR-35, FR-36

## What it does

Turns a `Verdict` and its evidence into text a person can read, naming the
component that decided the status.

## Why it exists

The brief requires every decision to be traceable. More specifically, FR-36
requires the explanation to **name the deciding signal** — not narrate generally
about evidence. "Trusted sources contradict this" is a status; "the knowledge
graph holds a conflicting value: claim says 1950, graph holds ['1889']" is an
explanation.

This module is also where the project's most important wording rule is enforced
in exactly one place.

## How it works internally

Explanations are assembled **deterministically** from component scores. No
language model writes them, for three reasons:

1. The text must be reproducible (NFR-06).
2. A generated explanation could describe a decision the pipeline did not make.
3. A generated explanation of a hallucination-detection system's output would be
   the single unverified claim in the whole product.

`confidence_phrase()` is the only function that decides how a confidence is
worded. With `calibrated=True` it reads "calibrated confidence 0.84"; otherwise
"uncalibrated score 0.84 (not a probability)". Because the API, the dashboard and
any exported report all call it, ADR-005's rule holds across every surface at
once rather than being re-remembered in three places.

The payload includes: status and its plain-language meaning, the deciding
reason, the confidence phrase, supporting and contradicting counts, coverage,
cross-source agreement, named sources on each side, the graph path when present,
and explicit notes for two cases that would otherwise mislead —

- a `MISSING` graph result is spelled out as *"the graph has no such statement,
  which is not evidence against the claim"*;
- undated supporting passages are disclosed as not age-discounted.

## What alternatives exist

| Alternative | Why not |
|---|---|
| LLM-generated prose | non-reproducible, and it can describe a decision that did not happen |
| Attention weights (KGAT-style) | say where a model looked, not what rule decided |
| Executed reasoning programs (`pan2023programfc`) | genuinely better explanations; the program generator is an LLM, so a wrong plan yields a confidently wrong trace. Our counter-position is not "better" but "deterministic and auditable without trusting a model" |
| Return scores only, no prose | the component table is already there; a non-specialist cannot read it |

## What could go wrong

- **A fluent explanation of a wrong verdict is more dangerous than a terse one.**
  The Marie Curie claim reads convincingly as `AMBIGUOUS` while being true.
- **Naming one deciding component oversimplifies.** Several signals usually
  contribute; the rule reports the branch that fired.
- **The text is English-only and not localised.**
- **Explanations are not summarised.** For a 25-claim document the dashboard
  shows 25 of these, which is thorough rather than readable.

## How it is tested

13 tests. They assert the deciding reason appears, that an uncalibrated score is
never called a probability, that `UNVERIFIABLE` says the claim *may still be
true*, that a `MISSING` graph result is explained as not-evidence-against, that
the graph path is rendered, that undated evidence is disclosed, that a
claim-level error is surfaced rather than swallowed, that the output is
deterministic, and that every status has a defined meaning.
