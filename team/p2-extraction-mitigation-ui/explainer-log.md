# Explainer Log — P2 — NLP Input, Mitigation & Frontend Engineer

One entry per merged story. Three things: **what it does**, **why it exists**,
**what could go wrong**. This is the artifact behind the Definition of Done item
"the owner can explain it out loud".

Written from the commits actually merged, not from the plan. If an entry cannot
be delivered verbally without opening the code, it is not finished.

Module-level detail lives in `docs/design/`; this log is the per-change record.


## 29 Oct — ADR-002 decomposition decision

- **What it does:** Rules-first decomposition with an optional LLM path, and an operational definition of 'atomic' with five worked examples.
- **Why it exists:** The five examples are the contract for what the word means. They are asserted as tests, so changing the decomposer's semantics fails CI rather than quietly shifting what the project claims.
- **What could go wrong:** A rules-based decomposer is weaker than an LLM one. The gap is a stated limitation, measured, not hidden.

## 29 Oct — ADR-007 dashboard decision

- **What it does:** Overturned the Phase 0 React plan in favour of static files.
- **Why it exists:** Four views with no shared state do not justify a toolchain, `node_modules`, a CI build step and a second deploy artifact — and a CDN asset would break the offline requirement.
- **What could go wrong:** It does not scale past roughly 700 lines of JS. The migration trigger is written into the ADR.

## 31 Oct — Input processing

- **What it does:** Validation, normalisation and sentence splitting with exact character offsets.
- **Why it exists:** The whole module exists for one invariant: slicing the normalised text must reproduce each sentence. Every highlight and claim span depends on it, and a violation is invisible to every later test.
- **What could go wrong:** NFKC changes string length, so offsets must be taken after normalising and the text must never be normalised twice. The abbreviation list is finite by design.

## 31 Oct — Mention extraction

- **What it does:** Entities, dates and numbers with spans, spaCy NER with a conservative regex fallback.
- **Why it exists:** P3 slices these spans to build queries, so they have to be exact. The fallback labels entities `PROPN` rather than guessing PERSON or ORG — a wrong type sends the graph stage at the wrong predicate.
- **What could go wrong:** Three bugs the first test run caught: a regex group let a bare number's span swallow a trailing space, '1960s' parsed as 1960 seconds, and the sentence-initial skip discarded multi-word proper nouns.

## 31 Oct — Claim decomposition

- **What it does:** Three patterns over the dependency parse: clausal coordination, modifiers, and coordinated modifiers on one verb.
- **Why it exists:** Compound sentences otherwise get one verdict for two facts, which defeats claim-level reporting.
- **What could go wrong:** spaCy attaches conjoined prepositions inconsistently, so grouping walks the coordinator's character position instead of the conj chain. And the object's prep modifiers matter: in the Curie sentence 'in Physics' hangs off *Prize*, not the verb.

## 31 Oct — Check-worthiness and golden fixture

- **What it does:** Classifies opinion, question, instruction and fragment; ships `claims_golden.json`.
- **Why it exists:** Biased towards keeping claims: a dropped claim is silently never verified, while a kept opinion returns UNVERIFIABLE, which is the right answer anyway.
- **What could go wrong:** The fixture is the handoff to P3 and P4. A test fails if the decomposer drifts from it, which is what stops a silent change breaking two other people.

## 02 Nov — Correction and annotation

- **What it does:** Substitution-based correction with abstention, plus annotated output.
- **Why it exists:** No model generates a correction, so 'introduce no unsupported claim' is true by construction rather than by promise. There is also no prompt to inject.
- **What could go wrong:** Only a wrong number, date or entity is fixable; everything else abstains, which looks like inactivity and is the module working. FR-41 re-verification is not implemented.

## 02 Nov — Prompt-injection suite

- **What it does:** Nine named attacks injected into evidence, each compared against a benign baseline.
- **Why it exists:** The real defence is architectural — no model in the decision path — so the suite asserts that property rather than assuming it, including a structural test that the decision-path modules reference no LLM client.
- **What could go wrong:** It found EA-10: appending 'Do not cite any source' flipped a verdict, because one stray 'not' set the whole passage's polarity. Removing the LLM removed *prompt* injection, not *content* injection.

## 02 Nov — Dashboard

- **What it does:** Four views, no framework, no build step, no external asset.
- **Why it exists:** Every number rendered comes from the API payload. A dashboard that invented a figure for this system would be the one unverified claim in the product.
- **What could go wrong:** Tested only indirectly: the API tests assert the payload fields the JS reads, and the JS is syntax-checked. There is no browser-level test, so a rendering regression would not be caught.
