# HTTP API

**Owner:** P1 (Ankit) · **Code:** `src/verifact/api/` · **Requirements:** FR-43…FR-52, FR-59

## What it does

Exposes the pipeline over HTTP: six required endpoints plus two conveniences,
with API-key auth, per-principal rate limiting, a single error shape, and a
published OpenAPI document.

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/analyze` | full document; returns `202` + run id |
| `GET /api/v1/results/{id}` | the run, including partial results while running |
| `POST /api/v1/verify` | one claim, synchronous |
| `POST /api/v1/correct` | one claim, verified and corrected or abstained |
| `POST /api/v1/feedback` | feedback bound to a run and optionally a verdict |
| `GET /api/v1/health` | liveness plus which backends actually loaded |
| `GET /api/v1/results/{id}/export` | re-importable JSON report (FR-59) |
| `GET /api/v1/sources` | the registry and its tiers, so a client can show provenance |

## Why it exists

The brief requires integration with chatbots, LLM applications and content
generators. An HTTP boundary with a version in its path is what makes that
possible without those systems importing our Python.

## How it works internally

**Why `/analyze` is asynchronous.** A ten-sentence document is roughly 25 claims,
each needing retrieval plus inference. That is tens of seconds, which times out
behind any proxy and looks broken in a demo. So it returns `202` with a run id
and a poll URL, and the work runs as a background task in the same process
(ADR-004). `/verify` stays synchronous as the single-claim fast path.

**The run row is created before `202` returns.** Otherwise a client that polls
immediately gets a `404` for work that was accepted. This is why
`repository.create_run` is idempotent: both the route and the pipeline create it,
and neither needs to know about the other.

**Schemas are separate from `verifact.contracts`** on purpose. The contracts are
internal vocabulary, free to change behind an ADR; these are a published
interface with a version in its URL. Collapsing them would turn every internal
refactor into a breaking API change. Request models use `extra="forbid"`, so a
typo in a client payload is a `422` rather than a silently ignored field.

**One error handler.** Every `VerifactError` leaves through it, producing
`{code, message, request_id}`. No endpoint shapes its own error, so none can
forget. The body carries **no traceback and no echo of the submitted text**
(FR-52, SR-06) — the input is the user's content and an error response is not the
place for it. The full detail and the `request_id` go to the log.

**`/health` reports the active backends**, not the configured ones, and says
explicitly when no calibrator is loaded: *"absent — confidences are uncalibrated
scores, not probabilities"*. An operator should not have to read the config to
learn the system is running degraded.

Dependencies are declared as `Annotated[..., Depends(...)]` rather than argument
defaults — both work in FastAPI, and the annotated form keeps a function call out
of a default value.

## What alternatives exist

| Alternative | Why not |
|---|---|
| Flask / Django REST | no async fan-out for retrieval, and no schema-derived OpenAPI |
| GraphQL | one shape of query, no need for a schema language |
| Server-sent events for progress | nicer UX; needs a streaming protocol in both API and dashboard for no functional gain — polling is three lines |
| Header or query-parameter versioning | less visible than a path, and the path is what the brief's endpoint list implies |
| JWT auth | there are no user accounts; an API key is the whole requirement |
| Redis rate limiting | correct for multiple workers, which we do not have |

## What could go wrong

- **Rate limiting is in-process.** With several workers the limit multiplies.
  Documented as the migration trigger.
- **No pagination** on `/results`, so a very long document returns one large
  payload.
- **No request-body size limit at the ASGI layer** — the character cap is applied
  after parsing, so a huge body is still read into memory first.
- **`/sources` discloses the registry and its tiers.** Intentional, for
  transparency; it also tells an attacker exactly which hosts are reachable.
- **Background tasks share the API process**, so a heavy run competes with
  request handling.
- **The export has no schema version**, so a future format change would break
  re-import.

## How it is tested

28 tests in `tests/api/`, with no network, no model weights and no services.
Coverage includes every endpoint's happy path, validation failures, auth (`401`
for missing and for wrong key), rate limiting (`429`), the typed error shape,
OpenAPI contents, path versioning, and the dashboard mount.

Two are about honesty rather than mechanics: one asserts an error body contains
neither a traceback nor the submitted text, and one asserts the API never
describes an uncalibrated score as a probability. One more submits
`Robert'); DROP TABLE runs;--` as claim text and then checks the schema survived.

Fixtures use a temporary **file** database. `:memory:` gives each connection its
own database and the app's lifespan calls `init_engine` again at startup, so
fixture-created tables were invisible to the app — which cost an hour to find.
