"""FastAPI application assembly.

Owner: P1. Holds the app, the centralised exception handlers (FR-52, SR-06) and
the static dashboard mount (ADR-007).

Every error leaves through one of the handlers below, so no endpoint has to
remember to shape its own error response, and no traceback or echo of the
submitted text can reach a client.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from verifact import __version__
from verifact.api.schemas import ErrorResponse
from verifact.api.v1.routes import router as v1_router
from verifact.config import get_settings
from verifact.db import repository, session_scope
from verifact.db.session import init_engine
from verifact.errors import VerifactError
from verifact.logging import configure_logging, get_logger

_log = get_logger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

#: How long a run may sit in `running` before a restart is assumed.
STALE_RUN_AFTER = timedelta(minutes=30)

DESCRIPTION = """
Explainable hallucination detection and mitigation using trusted sources and
knowledge graphs.

**What this API reports.** Whether each factual claim in the submitted text is
*attributable to a configured set of trusted sources*. It does not determine
truth, and a claim it cannot verify is reported as `UNVERIFIABLE` - which means
no source covering it was found, not that it is false.

**Confidence.** The `calibrated` flag on every verdict says whether the
confidence has been calibrated on a held-out split. When it is `false` the
number is a raw score and must not be read as a probability.
"""


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging, open the database, and clean up interrupted runs."""
    settings = get_settings()
    configure_logging(
        level=settings.log.level,
        json_format=settings.log.json_format,
        redact=settings.log.redact_text,
    )
    init_engine(settings.database_url)
    try:
        with session_scope() as session:
            swept = repository.sweep_stale_runs(session, datetime.now(UTC) - STALE_RUN_AFTER)
        if swept:
            _log.info("startup sweep marked interrupted runs failed", extra={"n": swept})
    except Exception:  # noqa: BLE001 - a missing table must not block startup
        _log.warning("startup sweep skipped; has `alembic upgrade head` been run?")
    _log.info("verifact started", extra={"version": __version__})
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VeriFact",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        # Versioning lives in the path (FR-49); the docs follow it.
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    if settings.api.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.api.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    @app.exception_handler(VerifactError)
    async def verifact_error_handler(_request: Request, exc: VerifactError) -> JSONResponse:
        """Typed error body, no traceback, no echo of the input (FR-52, SR-06).

        The full detail goes to the log, where it is useful, and the client gets
        a stable `code` it can branch on plus a message safe to display.
        """
        request_id = str(uuid.uuid4())
        _log.warning(
            "request failed",
            extra={"code": exc.code, "request_id": request_id, "detail": exc.detail},
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=ErrorResponse(
                code=exc.code, message=exc.public_message, request_id=request_id
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        """Last resort. An unexpected error must not leak its internals."""
        request_id = str(uuid.uuid4())
        _log.exception("unhandled error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code="internal_error",
                message="An internal error occurred.",
                request_id=request_id,
            ).model_dump(),
        )

    app.include_router(v1_router)

    # The dashboard is served by this same process: one artifact, and it cannot
    # drift from the API version serving it (ADR-007).
    if WEB_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/", include_in_schema=False)
        async def dashboard() -> FileResponse:
            return FileResponse(WEB_DIR / "index.html")

    return app


app = create_app()
