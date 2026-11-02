"""The pipeline runner.

Owner: P1 (FR-43, FR-61, FR-62). Wires the stages together in the order the
architecture document specifies and persists results as they are produced.

Two properties this module is responsible for:

* **Failure isolation.** One claim raising must not void the run. Each claim is
  verified inside its own try/except and a failure is recorded on that claim's
  verdict (the failure-isolation table in the architecture doc).
* **Provenance.** Every run records the config hash, the model identifiers that
  actually ran, and per-stage timings (FR-62). Without it a result is not
  reproducible, and "which backend produced this number" becomes unanswerable -
  which matters because the lexical fallbacks are materially weaker than the
  transformer ones.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from pathlib import Path

from verifact.config import Settings, get_settings
from verifact.contracts import (
    AnalysisRun,
    Document,
    RunProvenance,
    RunStatus,
)
from verifact.db import repository, session_scope
from verifact.explain import attach_explanation
from verifact.extraction import extract_claims
from verifact.logging import get_logger
from verifact.mitigation import annotate, correct_claim
from verifact.retrieval.clients.http import SafeClient
from verifact.retrieval.registry import get_registry
from verifact.retrieval.retriever import retrieve_for_claim
from verifact.verification import verify_claim
from verifact.verification.calibrate import Calibrator

_log = get_logger(__name__)


def _model_versions(settings: Settings) -> dict[str, str]:
    """Record what actually ran, not what was configured.

    A configured transformer model that failed to load and silently fell back to
    the lexical backend would otherwise be indistinguishable from one that ran.
    """
    from verifact.retrieval.rankers import load_embedder
    from verifact.verification.nli import load_nli

    embedder = (
        None
        if settings.retrieval.backend == "lexical"
        else load_embedder(settings.retrieval.embedding_model)
    )
    nli = (
        None
        if settings.verification.backend == "lexical"
        else load_nli(settings.verification.nli_model)
    )
    return {
        "embedding": settings.retrieval.embedding_model if embedder else "lexical-fallback",
        "nli": settings.verification.nli_model if nli else "lexical-fallback",
        "extraction": settings.extraction.spacy_model,
        "kg": "wikidata" if settings.kg.enabled else "disabled",
    }


def build_provenance(settings: Settings, timings: dict[str, float]) -> RunProvenance:
    return RunProvenance(
        config_hash=settings.config_hash(),
        model_versions=_model_versions(settings),
        seed=settings.seed,
        timings_ms={k: round(v, 2) for k, v in timings.items()},
    )


def run_analysis(
    document: Document,
    settings: Settings | None = None,
    corpus_path: Path | None = None,
    persist: bool = True,
) -> AnalysisRun:
    """Run the full pipeline over a document.

    Results are written per claim as they complete, so a crash loses one claim
    and `GET /results/{id}` on a running job returns partial work.
    """
    cfg = settings or get_settings()
    registry = get_registry()
    asof = document.asof or date.today()
    calibrator = Calibrator.load(cfg.verification.calibrator_path)
    timings: dict[str, float] = {}

    if persist:
        with session_scope() as session:
            repository.create_run(session, document, build_provenance(cfg, timings))
            repository.set_run_status(session, document.id, RunStatus.RUNNING)

    started = time.perf_counter()
    claims = extract_claims(document, cfg.extraction)
    timings["extraction_ms"] = (time.perf_counter() - started) * 1000

    verdicts = []
    corrections = []
    all_passages = []

    with SafeClient(cfg.retrieval, registry) as client:
        for claim in claims:
            claim_started = time.perf_counter()
            if not claim.checkworthy:
                # Kept in the run so the dashboard can show what was skipped and
                # why, but never retrieved for: it would cost a network call to
                # verify an opinion.
                if persist:
                    with session_scope() as session:
                        repository.save_claim_result(session, document.id, claim, [], None, None)
                continue

            try:
                passages = retrieve_for_claim(
                    claim, client, cfg.retrieval.top_k, corpus_path, cfg.retrieval
                )
                verdict = verify_claim(claim, client, registry, asof, cfg, calibrator, corpus_path)
                verdict = attach_explanation(claim, verdict, passages)
                correction = correct_claim(claim, verdict, passages, cfg.verification)
            except Exception as exc:  # noqa: BLE001 - one claim must not void the run
                _log.exception(
                    "claim failed, continuing with the rest of the run",
                    extra={"claim_id": claim.id, "run_id": document.id},
                )
                from verifact.contracts import Verdict, VerdictStatus

                passages = []
                verdict = Verdict(
                    claim_id=claim.id,
                    status=VerdictStatus.UNVERIFIABLE,
                    confidence=0.0,
                    explanation="this claim could not be verified; the rest of the run completed",
                    error=f"{type(exc).__name__}: {exc}",
                )
                correction = None

            verdicts.append(verdict)
            all_passages.extend(passages)
            if correction is not None:
                corrections.append(correction)
            timings[f"claim_{claim.id[:8]}_ms"] = (time.perf_counter() - claim_started) * 1000

            if persist:
                with session_scope() as session:
                    repository.save_claim_result(
                        session, document.id, claim, passages, verdict, correction
                    )

    annotated = annotate(document, claims, verdicts)
    timings["total_ms"] = (time.perf_counter() - started) * 1000
    provenance = build_provenance(cfg, timings)

    if persist:
        with session_scope() as session:
            repository.finish_run(session, document.id, annotated, provenance)

    _log.info(
        "run complete",
        extra={
            "run_id": document.id,
            "n_claims": len(claims),
            "n_verdicts": len(verdicts),
            "total_ms": round(timings["total_ms"], 1),
        },
    )
    return AnalysisRun(
        id=document.id,
        status=RunStatus.DONE,
        document=document,
        claims=claims,
        verdicts=verdicts,
        corrections=corrections,
        passages=all_passages,
        annotated_text=annotated,
        provenance=provenance,
        created_at=datetime.now(UTC),
    )
