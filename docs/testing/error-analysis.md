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
