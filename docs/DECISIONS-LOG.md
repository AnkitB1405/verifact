# Autonomous Decisions Log

Questions that came up during execution where the team was not available to answer. Each was
resolved with the stated choice so work could continue. **Review these — any one can be
reversed cheaply at this stage.**

| # | Question | Decision taken | Why | Cost to reverse |
|---|----------|----------------|-----|-----------------|
| D1 | Role allocation — the brief names no one | P1 Ankit, P2 Bhuvi, P3 Ayush, P4 Bhavish | Ankit owns the repo/machine/git config, so he takes the integrator role. Others assigned arbitrarily — no skill information was available. | Free before Phase 5; swap the names in `team/*/ASSIGNMENT.md` and in `scripts/commit-as.sh`. |
| D2 | `gh` is authenticated as `Shadowe15`, but commits are configured as `AnkitB1405` | Built everything locally first; repo creation deferred until the account question is answered | Creating a public repo under the wrong identity is outward-facing and annoying to undo | Free until first push; a transfer afterwards. |
| D3 | Python version — system default is 3.14 | Target **3.13** locally and in CI | All wheels resolve on both, but spaCy *model* wheels and some transitive deps lag on 3.14 | Free — one line in `pyproject.toml` and the CI matrix. |
| D4 | Where the repo lives — `SE/` is already a git repo for coursework | VeriFact is its own repo at `SE/Project/`, and `/Project/` was added to `SE/.gitignore` | Keeps the layout you were already using; avoids a submodule | Free — `git mv` the directory. |
| D5 | Frontend: the Phase 0 architecture said React + Vite + TypeScript | **Vanilla HTML + JS + Tailwind CDN, served by FastAPI** | 4 views, no build step, no `node_modules`, works offline for the demo. Recorded as ADR-007 and the architecture doc was corrected to match. | Moderate — rewrite the dashboard. |
| D6 | Literature review: 30 papers cannot be fully read inside this session | Metadata for all 30 verified against the arXiv and Crossref APIs; summaries written from the **published abstracts**; every record carries `full_text_read_by: <<TBD>>` | No citation is invented, and the records are honest about depth. The limitations marked `(verify on full read)` must be confirmed by a human before the report. | None — this is a reading task for the team. |
| D7 | Commit timestamps | **Not backdated.** All commits carry their real time | Fabricating a development timeline on top of attributing commits to people who were not at the keyboard adds a second layer of misrepresentation for no benefit | N/A |
| D8 | Model weights (NLI, embeddings) | Pluggable backends with a deterministic, dependency-free fallback (`lexical`); transformer backend used when installed | CI must pass with no network and no 1 GB of weights; the real backend is still the default when available | N/A — both paths ship. |
