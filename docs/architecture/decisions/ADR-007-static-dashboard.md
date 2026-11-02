# ADR-007 — Static dashboard served by FastAPI instead of a React build

- **Status:** Accepted · **Date:** 2026-10-29 · **Owner:** P2 (Bhuvi) · **Reviewed by:** P1
- **Supersedes:** the frontend row of the technology table in
  `docs/phase-0/02-preliminary-architecture.md §4`, which specified React + Vite + TypeScript

## Context

Phase 0 specified React + Vite + TypeScript + Tailwind + a graph library. On reaching Phase 3
and listing what the dashboard actually has to do — FR-53…FR-60 — it comes to four views:
enter text, claim list, claim detail (evidence + component scores), and an original/corrected
diff. There is no routing, no authentication UI, no client-side data model, and no shared
state beyond "the current run".

Against that, a React build brings: Node and npm on every machine, a `node_modules` tree, a
build step in CI, a second artifact to deploy, generated API types to keep in sync, and a
lockfile to audit for vulnerabilities. It also breaks the offline demo requirement (NFR-05)
unless the bundle is pre-built and committed.

## Decision

**One static HTML file, one hand-written stylesheet and one plain JS module, served by
FastAPI from `src/verifact/web/`.** No build step, no `node_modules`, no framework, and - as
built - **no external asset at all**.

The original decision said "Tailwind via CDN, vendored for offline use". On implementation
that vendoring step turned out to be the only thing standing between the dashboard and being
genuinely self-contained, and the whole dashboard needs about 160 lines of CSS. Writing them
removed a vendored third-party file, a licence to track and a dependency to audit, so the
stylesheet is hand-written instead. Recorded here rather than silently diverging from the
ADR.

## Consequences

- `git clone && make dev` gives a working dashboard. No Node required anywhere, including CI,
  and no network request for an asset.
- One deployable artifact; the dashboard cannot be out of step with the API version serving it.
- Offline demo works, as required.
- **What we give up:** component reuse, type-checked API responses in the frontend, and
  comfortable growth past ~700 lines of JS. If the UI grows a fifth and sixth view with shared
  state, this decision should be revisited — that is the migration trigger.
- FR-60 (KG subgraph visualisation) is implemented as inline SVG rendered from the API's path
  data rather than with a graph library. Acceptable for a path of a handful of nodes; it would
  not be acceptable for a dense graph.
- The dashboard must still not invent numbers: every value rendered comes from the API payload
  (FR-56), and there is a smoke test asserting the payload fields the page reads.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| React + Vite + TS (the Phase 0 plan) | an entire toolchain and a second deploy artifact for four views; breaks the offline requirement |
| Next.js | adds SSR and a Node runtime in production for a page with no SEO or server-rendering need |
| Streamlit / Gradio | fastest to write, but we would not control the layout required by FR-55…FR-58, and it is a second web server |
| Jinja templates server-rendered | reasonable, but every interaction becomes a round trip, and the claim detail view is inherently client-side |
