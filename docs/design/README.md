# Module Design Documents

One document per module. Each answers the six questions the brief sets for every
major component (§13): what it does, why it exists, how it works internally,
what alternatives exist, what could go wrong, and how it is tested.

They are written to be read aloud. If a section cannot be explained from the
document without opening the code, the document is wrong.

| Module | Owner | Document |
|---|---|---|
| Input processing | P2 Bhuvi | [`input.md`](input.md) |
| Claim extraction | P2 Bhuvi | [`extraction.md`](extraction.md) |
| Evidence retrieval | P3 Ayush | [`retrieval.md`](retrieval.md) |
| Knowledge graph | P3 Ayush | [`knowledge-graph.md`](knowledge-graph.md) |
| Verification engine | P4 Bhavish | [`verification.md`](verification.md) |
| Explainability | P4 Bhavish | [`explainability.md`](explainability.md) |
| Correction & mitigation | P2 Bhuvi | [`mitigation.md`](mitigation.md) |
| Platform: contracts, config, persistence, orchestration | P1 Ankit | [`platform.md`](platform.md) |
| HTTP API | P1 Ankit | [`api.md`](api.md) |
| Dashboard | P2 Bhuvi | [`dashboard.md`](dashboard.md) |

## The one rule that shapes all of them

Modules depend on `verifact.contracts` and never on each other. `extraction`
does not import `retrieval`; the orchestrator passes contract objects between
stages. Every "how it works internally" section below can therefore be read
without reading any other document.

## Reading order for someone new

`platform.md` (the contracts everything else speaks) → `input.md` →
`extraction.md` → `retrieval.md` → `knowledge-graph.md` → `verification.md` →
`explainability.md` → `mitigation.md` → `api.md` → `dashboard.md`.

That is also the order data flows through a run.
