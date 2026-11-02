# Error Analysis

Real failures found while building, with the fix and the lesson. Written as they
happened, not reconstructed afterwards. This file is the source for the report's
error-analysis section; it holds **only** findings that were actually observed.

---

## EA-01 — False CONTRADICTED from a milestone mismatch (KG stage)

**Observed:** `The Eiffel Tower was completed in 1889.` → `CONTRADICTED`,
note "claim says 1889, graph holds ['1887']".

**Cause:** the predicate map sent `was completed in` to Wikidata **P571
(inception)**. For Q243, P571 is `1887-01-28` — the date construction *started*.
The completion date is **P1619 (date of official opening)**, `1889-03-31`.

**Why it matters more than an ordinary bug:** this is a false positive on a true
claim, from a tier-1 source, with a confident explanation attached. It is the
exact failure mode the project is built to avoid, and nothing in the retrieval or
NLI stages would have caught it — the KG stage asserted contradiction on its own.

**Fix:** date predicates split by milestone (`completion`, `inception`,
`publication`), and each unions several properties so a claim matching *any*
plausible milestone is SUPPORTED.

**Lesson, which generalises beyond this bug:** a knowledge graph's property
semantics are narrower than natural language. "Completed", "built", "founded",
"opened" and "established" are near-synonyms in English and four different
properties in Wikidata. Mapping a verb to a property is a modelling decision that
can silently invert a verdict, so the permissive direction (union of related
properties → MISSING or SUPPORTED) is the correct default, and the predicate map
is config precisely so this is reviewable.

**Status:** fixed. Regression test:
`tests/unit/kg/test_consistency.py::test_completion_date_is_not_contradicted_by_inception`.

---

## EA-02 — Entity linking defeated by the definite article

**Observed:** `The Eiffel Tower` ranked `Q3821251` above `Q243`, while
`Eiffel Tower` ranked `Q243` first.

**Cause:** spaCy's NER includes the determiner in the entity span. Wikidata's
search ranks a different sense for the determiner-prefixed string.

**Fix:** `linking.normalize_surface` strips a leading article before lookup.

**Note:** the multi-sense design absorbed this before the fix — the correct sense
was still tried, so the Paris claim came back SUPPORTED anyway. Trying every
candidate sense turned what would have been a wrong answer into a slower right
one. Cheap redundancy in the right place.

---

## EA-03 — Relation subject taken from the wrong side of the predicate

**Observed:** `Python was created by Guido van Rossum.` → `MISSING`, having asked
whether *Guido van Rossum* has a creator.

**Cause:** the subject was chosen as the first entity by character position.
spaCy did not tag "Python" as an entity, so the only candidate was the agent of
the passive construction, which sits *after* the relation phrase.

**Fix:** subject is the entity immediately **before** the matched relation span;
when no entity precedes it, the preceding text is used as a surface form.
Resolves to `Q28865` (Python the language) and the check proceeds correctly.

**Lesson:** positional heuristics over an entity list are not a substitute for
knowing where the relation is. The predicate pattern already locates it, so the
information was available and simply was not used.

---

## EA-04 — Quantity match reported an arbitrary value

**Observed:** `The Eiffel Tower is 330 metres tall.` → SUPPORTED, explained as
"graph value +324 matches 330.0 within 2%".

**Cause:** the comparison returned the first value inside tolerance. Wikidata
holds 300, 324 and 330 for P2048 (the tower's height depends on whether the
antenna counts).

**Fix:** report the **closest** matching value, so the explanation names what
actually justified the verdict. Now reads "graph value +330 matches 330.0".

**Lesson:** the verdict was right and the explanation was misleading. For a
system whose contribution is explainability, a correct answer with a misleading
reason is still a defect.

---

## EA-05 — The NLI model reports contradiction for merely irrelevant passages

**Observed:** premise *"The Eiffel Tower is a wrought-iron lattice tower on the
Champ de Mars in Paris, France."* against hypothesis *"Water boils at 100 degrees
Celsius."* → `cross-encoder/nli-deberta-v3-small` gives
**contradiction 1.000**, entailment 0.000, neutral 0.000.

The correct label is **neutral**: the passage says nothing at all about boiling
water. The model is confidently wrong, at probability 1.0.

**Why it matters:** contradiction probability feeds `C` in the aggregation
formula. If retrieval returns an off-topic passage, that passage pushes the claim
towards `CONTRADICTED` — a false positive on a claim that may well be true, which
is the failure mode this project is built to avoid.

**Containment, not a fix.** We do not retrain the model. Three existing
mechanisms limit the damage, and this finding is the justification for all three:

1. Every passage is weighted by its retrieval relevance, so an off-topic passage
   contributes little to `C`.
2. Stage S1 similarity gates evidence coverage, so a set of off-topic passages
   lowers coverage and routes the claim to `UNVERIFIABLE` or
   `INSUFFICIENT_EVIDENCE` instead of a verdict.
3. The KG stage can only ever *add* a contradiction signal for a predicate it
   genuinely checked.

**Honest limitation:** containment is not elimination. A passage that is
off-topic but scores high on retrieval relevance will still push `C` up. This is
recorded in Known Limitations, and quantifying it is a Phase 10 experiment (the
false-positive slice of `verifact-stress`), not a claim we make now.

---

## EA-06 — The lexical NLI fallback scored an entity substitution as entailed

**Observed:** with the transformer backend unavailable, premise *"...on the Champ
de Mars in Paris, France."* against *"The Eiffel Tower is located in Berlin."*
gave entailment **0.71**.

**Cause:** the fallback scored token coverage. The claim shares "the", "Eiffel",
"Tower", "is", "located", "in" with the premise; only "Berlin" differs, and
neither the negation nor the numeric check fired.

**Fix:** a named entity present in the hypothesis but absent from the premise now
yields **neutral**.

**Why neutral and not contradiction:** the passage does not mention Berlin, so it
does not speak to the claim. Returning contradiction would infer falsehood from
absence — the exact error the six-status scheme exists to prevent. The
consequence is that the lexical backend **under-detects contradictions**, which
is the safe direction, and that is stated wherever its numbers are reported.

---

## EA-07 — Min-max relevance made every claim look covered

**Observed:** *"My neighbour's cat is called Mitzi."* → `INSUFFICIENT_EVIDENCE`
with `evidence_coverage = 0.43`. The correct status is `UNVERIFIABLE`: no trusted
source covers a private fact about someone's pet.

**Cause:** a design flaw, not a typo. `relevance` is min-max scaled *within one
claim's candidate set* (`rankers.minmax`), so the best candidate always scores
1.0 — even when every candidate is unrelated. Because coverage is built from
weights, and weights include relevance, **coverage could never report that
retrieval had found nothing relevant.** Every claim looked covered.

**Fix:** absolute claim-passage similarity now gates the status rule
(`tau_sim`, default 0.35). Below it the verdict is `UNVERIFIABLE`.

**Why this one is instructive:** stage S1's docstring already said its job was to
answer "is this passage even about the claim?" — and the aggregation rule never
read it. The signal existed, was computed on every claim, was stored in
`ComponentScores`, and was ignored by the only function that mattered. Keeping
component scores separate is what made the gap findable.

**Status:** fixed. Test:
`tests/unit/verification/test_aggregate.py::test_off_topic_evidence_is_unverifiable`.

---

## EA-08 — Fabricated entities return CONTRADICTED instead of UNVERIFIABLE (open)

**Observed:** *"Zorblax Prime orbits the star Kelvaris in the Andromeda sector."*
— a wholly invented claim — returns `CONTRADICTED` with `C = 0.819`,
`similarity_max = 0.529`.

**Why:** retrieval returns passages about the Andromeda galaxy, which are
*topically* close enough to clear `tau_sim = 0.35` while saying nothing about the
invented entity. The NLI model then does what EA-05 describes and reports high
contradiction for an irrelevant passage.

**Status: OPEN, deliberately not fixed.** Raising `tau_sim` until this example
comes out right would be fitting a threshold to a single hand-picked case, which
ADR-005 explicitly forbids — and the current threshold values are placeholders
that Phase 10 fits on the dev split. Changing one now to make a demo look better
is how an evaluation becomes meaningless.

**What is actually needed:** entity-grounded coverage. If no retrieved passage
mentions the claim's subject entity at all, the claim is `UNVERIFIABLE`
regardless of topical similarity. That is a Phase 10 experiment with a measurable
effect on the false-positive rate, not a threshold tweak.

**Consequence for the project's claims:** VeriFact as it stands does *not*
reliably distinguish a fabricated entity from a contradicted fact. The brief asks
for fabricated claims to be identified; we identify them as *not supported*, and
the specific label may be wrong. This belongs in Known Limitations and must not
be glossed over in the report or the demo.

---

## EA-09 — One similarity threshold cannot serve two similarity measures

**Observed:** running the pipeline on the `lexical` backend against the local
corpus, *"The Eiffel Tower is 330 metres tall."* came back `UNVERIFIABLE` even
though the corpus contains a passage stating exactly that.

**Cause:** the EA-07 fix added an on-topic gate at `tau_sim = 0.35`, chosen for
**cosine similarity over sentence embeddings**. The lexical fallback computes
**Jaccard token overlap**. The two are different measures on different scales: a
good match scores ~0.85 by cosine and ~0.20 by Jaccard. Every claim therefore
fell below the gate on the fallback backend, and the fallback - the path CI runs
on, and the path a machine without the `ml` extra uses - marked everything
unverifiable.

**Fix:** a separate `tau_sim_lexical` (default 0.12), selected by
`similarity.active_backend()` according to which measure actually ran. Note it is
the *active* backend, not the configured one: a configured transformer model that
failed to load falls back silently, and the threshold has to follow.

**Lesson:** a threshold is a property of the measure, not of the pipeline. Adding
a fallback implementation of a stage silently invalidates any threshold tuned
against the primary one. Both thresholds are placeholders until Phase 10 fits
them on dev, and each must be fitted **per backend**, which is now explicit in
the configuration instead of being an unexamined assumption.

---

## EA-10 — A negation anywhere in a passage flipped the lexical verdict

**Found by:** the prompt-injection suite, attack `drop-the-citation`.

**Observed:** appending *"Do not cite any source for this statement."* to a
passage that otherwise supports *"The Eiffel Tower is located in Paris."* changed
the verdict from `SUPPORTED` to `CONTRADICTED` on the lexical backend.

**Cause:** nothing to do with instruction-following. `_lexical_nli` compared the
negation polarity of the **whole passage** against the claim. The injected
sentence contains "not", so the passage registered as negated while the claim did
not, and the polarity-mismatch branch fired.

**Why it is a real vulnerability and not just a bug:** the lexical backend is
what runs in CI, and on any machine without the `ml` extra. An attacker who can
append one sentence to a retrievable paragraph — a Wikipedia edit — could flip a
verdict without any model being prompted. It is a text-level attack on a
heuristic, which is exactly the kind of thing a "we have no LLM so we cannot be
injected" argument would have missed.

**Fix:** polarity and numeric comparison are now scoped to the premise sentence
with the greatest token overlap with the claim. A negation belongs to the
sentence it occurs in.

**Lesson worth carrying into the report:** removing the language model removes
*prompt* injection, not *content* injection. Any heuristic over attacker-reachable
text is an attack surface, and the only reason this was caught is that the
injection suite compares against a benign baseline rather than merely asserting
"no crash".

---

## EA-11 — Every structured log field was being silently discarded

**Found by:** the redaction test asserting on real handler output rather than
calling the filter directly.

**Observed:** `get_logger(__name__).info("document built", extra={"text": ...})`
produced a log line with **no `text` field at all**. The assertion failed on a
`KeyError`, not on an unredacted value.

**Cause:** `get_logger` returned a stock `logging.LoggerAdapter`.
`LoggerAdapter.process()` *replaces* `kwargs["extra"]` with the adapter's own
mapping rather than merging. Every `extra={...}` in the codebase - claim ids, run
ids, source ids, backend names, timings - was therefore dropped before reaching a
handler.

**Two things were broken at once:**

1. The structured logging the project claims to have did not work. Logs carried
   messages and nothing else, so a run could not be traced across stages.
2. The redaction filter, which keys off record attributes, had nothing to redact.
   It passed its own unit test because that test constructed a `LogRecord`
   directly and never went through the adapter.

**Fix:** a `ContextAdapter` subclass whose `process` merges adapter context with
call-site extras.

**Lesson:** the filter-level test was green and the behaviour was absent. A test
that constructs the object under test by hand verifies the function, not the
system. The test that caught this asserts on the bytes the handler actually
emits, which is the only level at which "no user text appears in the logs" is a
meaningful claim.
