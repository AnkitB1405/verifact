"""API v1 routes.

Owner: P1 (FR-43…FR-52). One module because there are six endpoints and
splitting them across six files would be filing, not architecture.

`/analyze` returns 202 and a run id: a ten-sentence document is tens of seconds
of work and would time out behind any proxy (ADR-004). `/verify` is the
synchronous single-claim fast path used by the dashboard and by integrators.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from verifact import __version__
from verifact.api.deps import CallerDep, SettingsDep
from verifact.api.schemas import (
    AnalyzeAccepted,
    AnalyzeRequest,
    ComponentHealth,
    CorrectRequest,
    CorrectResponse,
    ExportedReport,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    ResultsResponse,
    VerifyRequest,
    VerifyResponse,
)
from verifact.config import Settings
from verifact.contracts import RunStatus
from verifact.db import repository, session_scope
from verifact.db.session import get_session
from verifact.errors import InputValidationError
from verifact.explain import attach_explanation, confidence_phrase
from verifact.extraction import extract_claims
from verifact.input import build_document
from verifact.logging import get_logger
from verifact.mitigation import correct_claim, summarise
from verifact.orchestrator import build_provenance, run_analysis
from verifact.retrieval.registry import get_registry
from verifact.retrieval.retriever import retrieve_for_claim
from verifact.verification import verify_claim
from verifact.verification.calibrate import Calibrator

_log = get_logger(__name__)

router = APIRouter(prefix="/api/v1")

#: Annotated dependency, same reason as in api/deps.py: keeps the Depends() call
#: out of a default value.
SessionDep = Annotated[Session, Depends(get_session)]


def _single_claim(text: str, asof: date | None, settings: Settings):  # type: ignore[no-untyped-def]
    """Extract exactly one claim from a short input, or fail clearly."""
    document = build_document(text, asof=asof, extraction_settings=settings.extraction)
    claims = [c for c in extract_claims(document, settings.extraction) if c.checkworthy]
    if not claims:
        raise InputValidationError(
            "no check-worthy factual claim was found in the submitted text "
            "(it may be an opinion, a question or an instruction)"
        )
    return document, claims[0]


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health(settings: SettingsDep) -> HealthResponse:
    """Liveness plus which backends actually loaded (FR-46).

    Reports the *active* backends, not the configured ones: a transformer model
    that failed to load falls back silently, and an operator needs to see that.
    """
    from verifact.orchestrator.pipeline import _model_versions

    components: list[ComponentHealth] = []
    try:
        registry = get_registry()
        components.append(
            ComponentHealth(
                name="source_registry",
                ok=bool(registry.source_ids),
                detail=f"{len(registry.source_ids)} sources, {len(registry.allowed_hosts)} hosts",
            )
        )
    except Exception as exc:  # noqa: BLE001 - health must report, not raise
        components.append(ComponentHealth(name="source_registry", ok=False, detail=str(exc)))

    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        components.append(ComponentHealth(name="database", ok=True, detail="reachable"))
    except Exception as exc:  # noqa: BLE001
        components.append(ComponentHealth(name="database", ok=False, detail=str(exc)))

    calibrator = Calibrator.load(settings.verification.calibrator_path)
    components.append(
        ComponentHealth(
            name="calibrator",
            ok=True,
            detail=(
                f"loaded ({calibrator.method}, T={calibrator.temperature})"
                if calibrator
                else "absent - confidences are uncalibrated scores, not probabilities"
            ),
        )
    )

    overall = "ok" if all(c.ok for c in components) else "degraded"
    return HealthResponse(
        status=overall,
        version=__version__,
        config_hash=settings.config_hash(),
        components=components,
        model_versions=_model_versions(settings),
    )


@router.post(
    "/analyze",
    response_model=AnalyzeAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["analysis"],
)
def analyze(
    payload: AnalyzeRequest,
    background: BackgroundTasks,
    settings: SettingsDep,
    _caller: CallerDep,
) -> AnalyzeAccepted:
    """Queue a full-document analysis (FR-43)."""
    document = build_document(
        payload.text, asof=payload.asof, extraction_settings=settings.extraction
    )
    with session_scope() as session:
        repository.create_run(session, document, build_provenance(settings, {}))

    # Runs in this process (ADR-004). A restart loses the task and the startup
    # sweep marks the run failed rather than leaving it "running" for ever.
    background.add_task(run_analysis, document, settings, None, True)
    return AnalyzeAccepted(
        run_id=document.id,
        status=RunStatus.QUEUED,
        poll=f"/api/v1/results/{document.id}",
    )


@router.post("/verify", response_model=VerifyResponse, tags=["analysis"])
def verify(payload: VerifyRequest, settings: SettingsDep, _caller: CallerDep) -> VerifyResponse:
    """Verify a single claim synchronously (FR-44)."""
    document, claim = _single_claim(payload.claim, payload.asof, settings)
    asof = document.asof or date.today()
    passages = retrieve_for_claim(claim, None, settings.retrieval.top_k, None, settings.retrieval)
    verdict = verify_claim(
        claim,
        None,
        get_registry(),
        asof,
        settings,
        Calibrator.load(settings.verification.calibrator_path),
    )
    verdict = attach_explanation(claim, verdict, passages)
    return VerifyResponse(
        claim=claim,
        verdict=verdict,
        passages=passages,
        explanation=verdict.explanation,
        confidence_note=confidence_phrase(verdict),
    )


@router.post("/correct", response_model=CorrectResponse, tags=["analysis"])
def correct(payload: CorrectRequest, settings: SettingsDep, _caller: CallerDep) -> CorrectResponse:
    """Verify a claim and propose a grounded correction, or abstain (FR-45)."""
    document, claim = _single_claim(payload.claim, payload.asof, settings)
    asof = document.asof or date.today()
    passages = retrieve_for_claim(claim, None, settings.retrieval.top_k, None, settings.retrieval)
    verdict = verify_claim(
        claim,
        None,
        get_registry(),
        asof,
        settings,
        Calibrator.load(settings.verification.calibrator_path),
    )
    verdict = attach_explanation(claim, verdict, passages)
    correction = correct_claim(claim, verdict, passages, settings.verification)
    return CorrectResponse(
        claim=claim,
        verdict=verdict,
        correction=correction,
        explanation=verdict.explanation,
    )


@router.get("/results/{run_id}", response_model=ResultsResponse, tags=["analysis"])
def results(run_id: str, session: SessionDep) -> ResultsResponse:
    """Fetch a run, including partial results while it is still running (FR-47)."""
    run = repository.load_run(session, run_id)
    return ResultsResponse(
        run=run,
        status_counts=summarise(run.verdicts),
        partial=run.status in (RunStatus.QUEUED, RunStatus.RUNNING),
    )


@router.get("/results/{run_id}/export", response_model=ExportedReport, tags=["analysis"])
def export_report(run_id: str, settings: SettingsDep, session: SessionDep) -> ExportedReport:
    """Export a run as a re-importable JSON report (FR-59)."""
    run = repository.load_run(session, run_id)
    return ExportedReport(
        exported_at=datetime.now(UTC),
        run=run,
        status_counts=summarise(run.verdicts),
        meta={"version": __version__, "config_hash": settings.config_hash()},
    )


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["feedback"],
)
def feedback(
    payload: FeedbackRequest,
    _caller: CallerDep,
    session: SessionDep,
) -> FeedbackResponse:
    """Record user feedback against a run or a specific verdict (FR-48)."""
    feedback_id = repository.save_feedback(
        session, payload.run_id, payload.verdict_id, payload.label, payload.comment
    )
    return FeedbackResponse(feedback_id=feedback_id)


@router.get("/sources", tags=["ops"])
def sources(_response: Response) -> dict[str, object]:
    """The source registry, so a client can show what may be cited and its tier."""
    registry = get_registry()
    return {
        "sources": [
            {
                "id": sid,
                "name": registry.get(sid).name,
                "kind": registry.get(sid).kind.value,
                "reliability_tier": registry.get(sid).reliability_tier,
                "base_reliability": registry.get(sid).base_reliability,
                "halflife_days": registry.get(sid).halflife_days,
            }
            for sid in registry.source_ids
        ]
    }
