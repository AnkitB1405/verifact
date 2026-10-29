# ADR-004 — FastAPI BackgroundTasks + Postgres state instead of Celery + Redis

- **Status:** Accepted · **Date:** 2026-10-29 · **Owner:** P1 (Ankit)

## Context

A 10-sentence document is ~25 claims, each needing retrieval plus NLI over several passages.
NFR-02 targets p50 ≤ 60 s for such a document. That is far too long for a synchronous HTTP
request during a live demo, so `POST /analyze` must be asynchronous (FR-43, 202 + run id).

## Decision

`POST /analyze` creates the run row, returns `202 {run_id}`, and schedules the pipeline as a
**FastAPI background task in the same process**. Run and per-claim state live in Postgres;
`GET /results/{id}` reads it. No broker, no worker process.

## Consequences

- One process, one database. Nothing new to install or explain.
- Progress is durable at per-claim granularity because each claim's results are persisted as
  they complete — a crash loses one claim, not the run, and `/results` returns partial work.
- **What we give up:** a task killed by a process restart is not retried automatically. A run
  interrupted mid-flight stays `running` until a startup sweep marks stale runs `failed`
  (implemented, not assumed — tested in `test_persistence.py`).
- No horizontal scaling of workers. Irrelevant at one concurrent demo user; it becomes the
  migration trigger below.
- Long tasks occupy a thread in the API process, so the API must not be run with a thread
  pool of one. Documented in the deployment guide.

## Migration trigger

Adopt Celery + Redis when any is measured: more than ~5 concurrent analyses needed; retries
across process restarts become a requirement; or the API's p95 latency degrades because
background work starves request handling. The pipeline is already a pure function from
`Document` to `AnalysisRun`, so it can be moved behind a broker without touching the modules.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Celery + Redis | two more services and a second failure domain to support one demo user |
| Fully synchronous `/analyze` | 60 s HTTP requests time out behind any proxy, and the demo would look broken |
| Server-sent events / WebSocket streaming | nicer UX, but needs a streaming protocol in both API and dashboard for no functional gain; polling is three lines |
| In-memory job dict | state lost on restart, and verdicts must be persisted anyway for FR-61 |
