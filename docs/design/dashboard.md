# Dashboard

**Owner:** P2 (Bhuvi) · **Code:** `src/verifact/web/` · **Requirements:** FR-53…FR-60
**Decision:** ADR-007

## What it does

Four views served as static files by the same FastAPI process: enter text, claim
list, claim detail (evidence, component scores, graph path), and original versus
corrected.

## Why it exists

The component scores are the project's contribution, and a JSON payload does not
communicate them. The dashboard exists to make the *reasoning* inspectable, not
to look finished.

## How it works internally

One HTML file, one hand-written stylesheet, one plain ES module. No framework, no
build step, and no external asset of any kind.

ADR-007 originally specified React + Vite + TypeScript, then Tailwind via CDN
vendored for offline use. On implementation the vendored file turned out to be the
only thing keeping the dashboard from being self-contained, and the whole thing
needs about 160 lines of CSS — so the stylesheet is hand-written and the ADR was
corrected rather than left to diverge.

**The rule that governs the JS: every number rendered comes from the API
payload** (FR-56). Nothing is computed, re-rounded into a different meaning, or
inferred in the browser. If a value is not in the response it is not displayed.
A dashboard that invented a figure for a hallucination-detection system would be
the one unverified claim in the product.

The confidence badge follows `verdict.calibrated` exactly, printing "calibrated"
or "uncalibrated" — the same rule `confidence_phrase()` enforces server-side.

`/analyze` returns 202, so the page polls `/results/{id}` until `partial` is
false, rendering partial results as they arrive. The graph path is rendered as
text rather than with a graph library: for a path of a handful of nodes a
dependency is not justified (FR-60 is therefore partially met, and said so).

## What alternatives exist

| Alternative | Why not |
|---|---|
| React + Vite (the original plan) | a toolchain, `node_modules`, a build step in CI and a second deploy artifact, for four views with no shared state |
| Next.js | an SSR runtime in production for a page with no SEO need |
| Streamlit / Gradio | fastest to write; no control over the layout FR-55…FR-58 require, and a second web server |
| Server-rendered Jinja | reasonable, but the claim-detail view is inherently client-side and every interaction becomes a round trip |
| A graph library for the KG path | the path is 2–3 nodes |

## What could go wrong

- **It does not scale past roughly 700 lines of JS.** A fifth and sixth view with
  shared state is the migration trigger back towards a framework.
- **No accessibility audit has been done.** Keyboard selection and roles are
  present on the claim list; contrast and screen-reader behaviour are unverified.
- **25 explanation blocks for a 25-claim document** is thorough and not readable.
  There is no summarisation.
- **Polling has no backoff** and gives up after 120 attempts.
- **Errors surface the API's typed message only**, which is correct for privacy
  and sometimes thin for debugging.
- **One smoke test is not UI testing.** There is no browser-level test, so a
  rendering regression would not be caught by CI.

## How it is tested

Indirectly, and that is a stated weakness. `tests/api` asserts the page is served
and that the payload contains every field the JS reads, so a contract change that
would blank a panel fails CI. The JS itself is checked for syntax only. The
dashboard was exercised by hand against a live server: 202 → poll → three
verdicts, annotated text, static assets at 200.
