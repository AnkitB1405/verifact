# Knowledge Graph

**Owner:** P3 (Ayush) · **Code:** `src/verifact/kg/` · **Requirements:** FR-20…FR-25
**Decision:** ADR-003 · **Produces:** `KGCheck`, and the `kgcheck_golden.json` fixture

## What it does

Maps a claim to a (subject, predicate, object) triple, resolves the entities to
Wikidata identifiers, and checks whether the graph holds, contradicts, or is
silent about that relation.

## Why it exists

Text entailment and graph lookup fail differently. NLI reads prose and is fooled
by topical similarity; a graph lookup is categorical and is defeated by missing
data. Running both and keeping the signals separate is what lets the aggregation
rule prefer the one that actually knows.

**The single most important rule in the module:**

> An absent relation yields `MISSING`, never `CONTRADICTED`.

Wikidata not holding a fact is *silence, not denial*.
`shiralkar2017streams` — genuine, elegant KG fact-checking — is limited by
exactly this conflation: a sparse region of the graph gives a low score for a
true fact. If this module ever returned `CONTRADICTED` for an absent relation,
the whole system would become a false-positive machine.

## How it works internally

**Predicate map** (`config/kg_predicates.yaml`) — relations are *data*, not code,
so the supported set is enumerable when an examiner asks "what exactly can your
graph check?" Each entry carries Wikidata property ids, a value type (entity,
time, quantity), a transitivity flag, surface patterns, and a tolerance for
quantities. An unmatched relation returns `NOT_APPLICABLE`, which is honest and
very different from `MISSING`.

**Entity linking** — candidates are ranked by exact-label match, Wikidata's own
result position, and whether a description exists. Surface form alone cannot
disambiguate "Washington" (state, city, surname, given name) or "Eiffel Tower"
(the tower, and two paintings of it), **so the module does not try.** It flags the
mention ambiguous and passes the whole candidate list on.

**Disambiguation is by relation, not by popularity.** The consistency check tries
each candidate sense and:

- any sense for which the relation holds → `SUPPORTED` (the claim asserts
  something true of one sense, which is enough);
- every sense carrying the relation conflicting → `CONTRADICTED`;
- no sense carrying the relation → `MISSING`.

That ordering means **ambiguity can never manufacture a false contradiction.**

**Subgraph construction** — breadth-first from the subject, following *only* the
predicates under test, bounded by hop count and a node cap. Restricting the walk
is what keeps it small: following every relation from a city would reach thousands
of nodes in one hop, none of them relevant.

**Transitivity is why a graph is needed at all.** Wikidata records the Eiffel
Tower's `located in the administrative territorial entity` as the 7th
arrondissement (Q259463), *not* Paris (Q90). Checking the direct statement alone
would return `CONTRADICTED` on a true claim. Walking reaches Paris in two hops,
and the measured subgraph for that claim is **5 nodes** — which is the evidence
behind ADR-003's choice of in-process NetworkX over a graph server.

The returned path is the explanation (FR-25): "Eiffel Tower → 7th arrondissement
→ Paris" is auditable; "true" is not.

## What alternatives exist

| Alternative | Why not |
|---|---|
| Neo4j | a server, driver, query language and deployment story, to hold a few hundred nodes at a time (ADR-003 lists four measured migration triggers) |
| RDFLib + triplestore | real RDF semantics, but heavy and slow to load, and Wikidata already speaks SPARQL |
| SPARQL per check instead of a local graph | a bespoke query per predicate pattern, no path to show, and a round trip per check |
| `wbgetentities` → chosen | one cached call returns a full one-hop neighbourhood, which is exactly what the subgraph builder needs |
| Pick the most popular entity sense | would make the stage confidently check the wrong entity; a wrong entity yields CONTRADICTED on a true claim |

## What could go wrong

- **Property semantics are narrower than natural language.** This produced the
  project's worst bug: "completed in" mapped to P571 (*inception* — 1887, when
  construction *started*) rather than P1619 (*official opening* — 1889), making a
  true claim `CONTRADICTED` with a confident explanation (EA-01). Date
  predicates are now split by milestone and union related properties.
- **Only the listed predicates are checkable.** Everything else is
  `NOT_APPLICABLE`, so most real-world claims get no graph signal at all.
- **An outdated graph is confidently wrong.** There is no temporal reasoning over
  statement qualifiers.
- **Transitive walking can over-reach**: a long chain of `located in` could reach
  a continent and support an absurdly coarse claim.
- **The cache is load-bearing.** Without it every run re-queries Wikidata, which
  is why cache behaviour is a tested requirement rather than an optimisation.

## How it is tested

35 tests. Pure comparison helpers run without network; the four `KGCheck`
outcomes are asserted against live Wikidata under the `network` marker. The
decisive test is `test_absent_relation_is_missing_never_contradicted`. EA-01 has
a named regression test, as do the subject-selection and quantity-reporting bugs.
