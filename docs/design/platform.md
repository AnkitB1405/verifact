# Platform: Contracts, Configuration, Persistence, Orchestration

**Owner:** P1 (Ankit) · **Code:** `src/verifact/{contracts,config.py,logging.py,errors.py,db,orchestrator}/`
**Requirements:** FR-61…FR-63, NFR-06, NFR-15, SR-04, SR-07, SR-08 · **Decision:** ADR-004

## What it does

Holds the shared vocabulary every module speaks, the single place configuration
lives, the database mapping, and the runner that wires the stages together.

## Why it exists

Four people worked on this codebase in parallel for one week. The thing that made
that possible is a single rule:

> Modules depend on `verifact.contracts` and never on each other.

`extraction` does not import `retrieval`. The orchestrator passes contract
objects between stages. Every module is therefore unit-testable from a fixture,
and the handoffs between people became *files* (`claims_golden.json`,
`evidence_golden.json`, `kgcheck_golden.json`) rather than "wait for my branch".

## How it works internally

**Contracts** — 17 Pydantic models, frozen and `extra="forbid"`, so a typo in a
field name is an error rather than a silently ignored attribute. Invariants live
in the models, not in convention:

- an abstained `Correction` must carry a reason and no text; a non-abstained one
  must carry text *and* at least one citation;
- `Verdict.calibrated` defaults to `False`, and only the calibration stage sets
  it `True`, so **no stage can claim a calibration it does not have**;
- `KGStatus.MISSING` exists specifically so an absent relation is distinguishable
  from a contradicted one.

**Configuration** — one settings object, nested per module, assembled from
environment and optional YAML. Nobody reads `os.environ` directly, so every knob
is discoverable and typed. Two deliberate behaviours: startup **fails** if auth
is enabled with no keys configured rather than serving an open endpoint, and
`config_hash()` covers everything that can change a *result* while excluding log
level and auth — so changing verbosity does not mark every past run
irreproducible.

**Logging** — JSON with a redaction *filter*, not a call-site convention, because
a convention gets broken by whoever adds the next log line (NFR-15). The adapter
had to be subclassed: `logging.LoggerAdapter.process` *replaces* `kwargs["extra"]`
rather than merging, so every structured field in the codebase was being silently
discarded and the redaction filter had nothing to redact — while its own unit
test passed, because that test built a `LogRecord` by hand (EA-11).

**Errors** — one class per error the API can return, each with a stable `code`, an
HTTP status and a message safe to display. Full detail goes to the log; the
client never sees a traceback or an echo of its own input.

**Persistence** — SQLAlchemy ORM only, no SQL built from strings (SR-04). `JSONB`
on PostgreSQL and `JSON` on SQLite via a type variant, so a clone runs with no
services while production keeps JSONB's operators. Foreign keys are switched on
explicitly for SQLite, or the `ON DELETE CASCADE` rules would silently not apply
in development. The score bag and provenance are JSON because they are only ever
read whole and their shape grows — a column per component score would mean a
migration every time a signal is added.

**Orchestration** — each claim is verified inside its own try/except, so one
claim raising records an error on that claim's verdict and the run completes.
Results are written **per claim** as they complete: a crash loses one claim, not
the run, and `GET /results/{id}` on a running job returns finished work.

Provenance records the backends that **actually ran**, not the configured ones.
A transformer model that fails to load falls back silently, and
`"lexical-fallback"` in `model_versions` is the only way a reader can tell a
degraded result from a normal one. The fallbacks are materially weaker, so this
is a correctness concern, not bookkeeping.

## What alternatives exist

| Alternative | Why not |
|---|---|
| Celery + Redis | two more services and a second failure domain to support one demo user (ADR-004 records the migration trigger) |
| Synchronous `/analyze` | 60-second HTTP requests time out behind any proxy |
| In-memory job dict | state lost on restart, and verdicts must be persisted for FR-61 anyway |
| Reuse the contracts as API schemas | every internal refactor becomes a breaking API change |
| Mutable contracts | stages would mutate shared objects and the cause of a changed score would be unfindable |
| Postgres required for development | a clone would need Docker before a single test could run |

## What could go wrong

- **A background task killed by a restart is not retried.** A startup sweep marks
  runs stale after 30 minutes rather than leaving them `running` for ever — which
  is a mitigation, not a fix.
- **The rate limiter is per-process.** With more than one worker the effective
  limit multiplies by the worker count.
- **Long tasks occupy a thread** in the API process, so a single-thread pool
  would starve request handling.
- **Contract changes are expensive by design** and three people feel every one.
- **Per-claim commits mean more transactions**, traded deliberately for
  durability and partial results.
- **SQLite and PostgreSQL differ** in JSON operators and type affinity; tests run
  on SQLite, so a Postgres-only behaviour could pass CI and fail in compose.

## How it is tested

12 integration tests plus the contract round-trips. The integration suite covers
persistence round-trip (including that component scores survive), provenance,
determinism, the stale-run sweep, and a **simulated mid-run stage failure** that
must leave the run `done` with exactly one errored verdict. Migrations are
verified in CI by `upgrade head → downgrade base → upgrade head`, which must
leave only `alembic_version` behind (FR-63).
