# ADR-003 — NetworkX in-process instead of a graph database

- **Status:** Accepted · **Date:** 2026-10-29 · **Owner:** P3 (Ayush) · **Reviewed by:** P1

## Context

The brief explicitly says not to introduce a heavyweight graph database without demonstrating
why it is necessary. The KG stage must, per claim: resolve entities to Wikidata QIDs, fetch a
bounded k-hop neighbourhood, and check whether a specific relation holds, contradicts, or is
absent.

The determining fact: **we never query a large graph.** We query Wikidata over SPARQL for a
small neighbourhood, then reason over that neighbourhood. Measured bound from the design: a
2-hop neighbourhood restricted to our supported predicates is in the hundreds of nodes, with
a configured cap (FR-22).

## Decision

**NetworkX `DiGraph`, built per claim in-process from cached Wikidata SPARQL results.**
No persistent graph store.

## Consequences

- No extra service to install, operate, back up, or explain. `docker compose up` stays two
  containers.
- Subgraph construction is a pure function of its inputs, so it is trivially testable from a
  fixture (`kgcheck_golden.json`) and deterministic.
- **We lose** persistence of the accumulated graph, cross-claim graph queries, and anything
  resembling graph analytics at scale. We do not currently need any of them.
- The HTTP cache becomes load-bearing: without it, every run re-queries Wikidata. Cache
  behaviour is therefore a tested requirement (FR-17), not an optimisation.

## Migration trigger (so this is a decision, not an assumption)

Move to a persistent store **only** when one of these is measured, not anticipated:

1. A single claim needs a neighbourhood above the node cap (≫ 10³ nodes), or ≥ 3 hops.
2. Verification requires queries across claims or across runs (e.g. consistency of a whole
   document against a graph built from all its claims).
3. Subgraph construction exceeds ~25% of per-claim latency even with a warm cache.
4. We want to persist and version a curated graph as a project artifact.

Migration path if triggered: keep `kg/consistency.py` unchanged — it consumes a graph
interface — and replace `kg/subgraph.py` with a Neo4j-backed implementation of that same
interface. The interface boundary exists **now**, precisely so the migration is one file.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Neo4j | a server, a driver, a query language and a deployment story, to hold a few hundred nodes at a time |
| RDFLib + a triplestore | genuine RDF/SPARQL semantics locally, but heavy, slow to load, and we already get SPARQL from Wikidata itself |
| Query Wikidata SPARQL directly for each check, no local graph | needs a bespoke SPARQL query per predicate pattern, cannot show a path, and makes every check a network round trip |
