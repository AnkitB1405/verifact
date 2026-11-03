# Claim Extraction

**Owner:** P2 (Bhuvi) · **Code:** `src/verifact/extraction/` · **Requirements:** FR-07…FR-12
**Decision:** ADR-002 · **Produces:** `list[Claim]`, and the `claims_golden.json` fixture

## What it does

Decomposes each sentence into atomic factual claims, annotates each with
entities, dates and numbers, and classifies whether it is worth verifying.

## Why it exists

Two reasons, both load-bearing.

**Claim-level reporting needs claim-level units.** A verdict on "The Eiffel
Tower, completed in 1889, is 330 metres tall" is useless: one half may be right
and the other wrong. FActScore (`min2023factscore`) established this, and our
operational definition follows it:

> A claim is atomic when it asserts exactly one relation between resolved
> arguments, and removing any part of it destroys the assertion.

**Everything downstream costs money.** Retrieval is a network call and NLI is
model inference, per claim. Verifying an opinion spends both to produce a
meaningless answer.

## How it works internally

Three decomposition patterns over the spaCy dependency parse:

1. **Clausal coordination** — conjoined verbs are split; a conjunct without its
   own subject inherits the first clause's subject.
2. **Appositive, relative and participial modifiers** — "…, completed in 1889, …"
   yields a separate claim. These are *reconstructed* sentences, so `Claim.text`
   is not a substring of the source and the span points at the region it came
   from.
3. **Coordinated modifiers on one verb** — "won the Nobel Prize in Physics in
   1903 and in Chemistry in 1911" yields one claim per conjunct.

Two implementation details that were not obvious and cost real debugging:

- **Grouping uses the coordinator's character position**, not a walk of the
  `conj` chain. spaCy attaches conjoined prepositions inconsistently — sometimes
  under the first preposition, sometimes under its object — and a tree walk
  produced *overlapping* groups.
- **The direct object's prepositional modifiers must be considered too.** In the
  Curie sentence spaCy attaches "in Physics" to *Prize* and "in 1903" to *won*.
  Looking only at the verb's children left "in Physics" stranded in the shared
  stem, so the second claim came out as "…in Physics in Chemistry in 1911".

Check-worthiness is a lexicon-and-structure classifier: questions by terminal
punctuation, imperatives by a sentence-initial base-form verb with no subject,
opinions by stance verbs, evaluative adjectives and normative modals, fragments
by the absence of any verb. It is **biased towards keeping claims** — a dropped
claim is silently never verified, while a kept opinion returns `UNVERIFIABLE`,
which is the right answer for a subjective statement anyway.

Span convention: `Claim` offsets index into `Document.normalized_text`; mention
offsets index into `Claim.text`, because a reconstructed claim has no exact
counterpart in the document.

## What alternatives exist

| Alternative | Why not |
|---|---|
| LLM decomposition (FActScore's own method) | non-reproducible, may need a key we do not have, and puts an unauditable model at the head of the pipeline (ADR-002) |
| Fine-tune a decomposition model | no training data, no budget, no time |
| One claim per sentence | compound sentences get a single verdict — the exact failure FActScore identifies |
| Run a coreference resolver | adds a model and a failure mode for a gain we cannot measure in a week; flagging is cheaper and safer |

## What could go wrong

- **Coreference is not resolved.** "He later moved to Berlin" is flagged
  `standalone_interpretable=False` and routed to `AMBIGUOUS` (FR-11). A *guessed*
  referent would produce a confidently wrong verdict, which is worse.
- **Implicit and presupposed claims are missed.** "the former president" does not
  yield "X was president".
- **Nested coordination beyond one level** is left as a single claim. Asserted as
  a test so the limitation is a measured fact rather than a caveat.
- **The regex fallback is markedly weaker** — semicolons and ", and" only.
- **Reconstruction can produce slightly unnatural English**, since modifiers are
  rebuilt with a copula. The claim is still checkable; it just does not read like
  the original.

## How it is tested

47 tests across `tests/unit/extraction/`. All five ADR-002 worked examples are
asserted, so breaking the published definition of "atomic" fails CI. The
documented limitations have their own tests. `claims_golden.json` is regenerated
deliberately and a test fails if the decomposer drifts from it — which is how P3
and P4 are protected from silent changes.
