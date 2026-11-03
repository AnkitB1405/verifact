# Explainer Log — P3 — Evidence & Knowledge Graph Engineer

One entry per merged story. Three things: **what it does**, **why it exists**,
**what could go wrong**. This is the artifact behind the Definition of Done item
"the owner can explain it out loud".

Written from the commits actually merged, not from the plan. If an entry cannot
be delivered verbally without opening the code, it is not finished.

Module-level detail lives in `docs/design/`; this log is the per-change record.


## 29 Oct — ADR-003 graph store decision

- **What it does:** NetworkX in-process rather than Neo4j, with four measured migration triggers.
- **Why it exists:** The decisive fact is that we never query a large graph — we fetch a small neighbourhood and reason over it. The Eiffel Tower location subgraph is 5 nodes.
- **What could go wrong:** No persistence and no cross-claim queries. The subgraph interface is separated now precisely so migration would be one file.

## 01 Nov — Source registry and SSRF controls

- **What it does:** Five justified reliability tiers; four SSRF controls with 20 tests naming the attack each blocks.
- **Why it exists:** The registry is the single allowlist — it decides both what may be cited and what may be contacted, so there is no second list to forget. The address check runs after DNS resolution, because an allowlisted *name* is not enough.
- **What could go wrong:** `is_global` is used instead of a CIDR list so it needs no maintenance. An unknown source goes to the lowest tier and is logged — dropping it would hide a coverage gap.

## 01 Nov — Clients, BM25, dense retrieval, RRF

- **What it does:** All outbound access through one SafeClient; two retrievers fused by reciprocal rank fusion.
- **Why it exists:** BM25 and embeddings fail in complementary ways — measured, not asserted: on a paraphrase with no shared vocabulary BM25 scores −0.28 and dense scores +0.41. Their scores are not comparable, so RRF fuses ranks.
- **What could go wrong:** Redirects are followed by hand so each hop is re-validated. The HTTP cache has no expiry, so a cached paragraph can be stale while the article has moved on.

## 01 Nov — Knowledge graph verification

- **What it does:** Entity linking, k-hop subgraph, consistency check with four outcomes.
- **Why it exists:** An absent relation is MISSING, never CONTRADICTED — Wikidata's silence is not denial, which is the limitation `shiralkar2017streams` could not escape. Ambiguity is resolved by the claim's own relation, never by popularity, so it cannot manufacture a false contradiction.
- **What could go wrong:** Only the listed predicates are checkable; everything else is NOT_APPLICABLE, so most real claims get no graph signal. There is no temporal reasoning, so an outdated graph is confidently wrong.

## 01 Nov — Golden fixtures and four written-up bugs

- **What it does:** Shipped `evidence_golden.json` and `kgcheck_golden.json`; documented EA-01 to EA-04.
- **Why it exists:** The fixtures mean P4's aggregation tests never touch a live API. EA-01 is the one to remember: 'completed in' mapped to P571 (inception, 1887) instead of P1619 (opening, 1889), making a true claim CONTRADICTED from a tier-1 source with a confident explanation.
- **What could go wrong:** A graph's property semantics are narrower than natural language. 'Completed', 'built', 'founded' and 'opened' are near-synonyms in English and four different properties in Wikidata.
