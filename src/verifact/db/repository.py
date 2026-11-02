"""Mapping between contracts and ORM rows.

Owner: P1. Kept in one module so the ORM never leaks into the pipeline and the
contracts never leak into the schema. Every stage works with Pydantic contracts;
only this file knows about both.

Per-claim writes are deliberate (FR-61, FR-62, and ADR-004's durability claim):
each claim's results are persisted as it completes, so a crash mid-run loses one
claim rather than the run, and `GET /results/{id}` on a running job returns the
work already finished instead of nothing.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from verifact.contracts import (
    AnalysisRun,
    Claim,
    ClaimType,
    Correction,
    Document,
    EvidencePassage,
    KGCheck,
    RetrievalScores,
    RunProvenance,
    RunStatus,
    Verdict,
)
from verifact.db.models import (
    ClaimRow,
    CorrectionRow,
    FeedbackRow,
    PassageRow,
    RunRow,
    VerdictRow,
)
from verifact.errors import RunNotFoundError
from verifact.logging import get_logger

_log = get_logger(__name__)


def create_run(session: Session, document: Document, provenance: RunProvenance) -> str:
    """Insert a queued run and return its id. Idempotent.

    Two callers legitimately create the same run: the `/analyze` route inserts
    it before returning 202, so an immediate `GET /results/{id}` finds a row
    rather than a 404, and the pipeline inserts it when invoked directly (CLI,
    tests, evaluation harness). Making this a no-op for an id that already
    exists lets both call it without the route and the pipeline needing to know
    about each other, and makes a retried background task harmless.
    """
    existing = session.get(RunRow, document.id)
    if existing is not None:
        return str(existing.id)
    row = RunRow(
        id=document.id,
        status=RunStatus.QUEUED.value,
        raw_text=document.raw_text,
        normalized_text=document.normalized_text,
        asof=document.asof,
        provenance=provenance.model_dump(mode="json"),
    )
    session.add(row)
    session.commit()
    return str(row.id)


def set_run_status(
    session: Session, run_id: str, status: RunStatus, error: str | None = None
) -> None:
    row = session.get(RunRow, run_id)
    if row is None:
        raise RunNotFoundError(f"run {run_id} not found")
    row.status = status.value
    if error is not None:
        row.error = error
    session.commit()


def save_claim_result(
    session: Session,
    run_id: str,
    claim: Claim,
    passages: list[EvidencePassage],
    verdict: Verdict | None,
    correction: Correction | None,
) -> None:
    """Persist one claim and everything derived from it, in one transaction."""
    session.add(
        ClaimRow(
            id=claim.id,
            run_id=run_id,
            sentence_idx=claim.sentence_idx,
            char_start=claim.char_start,
            char_end=claim.char_end,
            text=claim.text,
            claim_type=claim.claim_type.value,
            checkworthy=claim.checkworthy,
            standalone_interpretable=claim.standalone_interpretable,
            mentions={
                "entities": [e.model_dump(mode="json") for e in claim.entities],
                "temporal": [t.model_dump(mode="json") for t in claim.temporal],
                "numerics": [n.model_dump(mode="json") for n in claim.numerics],
            },
        )
    )
    for passage in passages:
        session.add(
            PassageRow(
                id=passage.id,
                claim_id=claim.id,
                source_id=passage.source_id,
                url=passage.url,
                title=passage.title,
                published_at=passage.published_at,
                text=passage.text,
                scores=passage.scores.model_dump(mode="json"),
            )
        )
    if verdict is not None:
        session.add(
            VerdictRow(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                status=verdict.status.value,
                confidence=verdict.confidence,
                calibrated=verdict.calibrated,
                component_scores=verdict.component_scores.model_dump(mode="json"),
                kg_check=verdict.kg_check.model_dump(mode="json") if verdict.kg_check else None,
                evidence_for=list(verdict.evidence_for),
                evidence_against=list(verdict.evidence_against),
                explanation=verdict.explanation,
                budget_spent=verdict.budget_spent,
                error=verdict.error,
            )
        )
    if correction is not None:
        session.add(
            CorrectionRow(
                id=str(uuid.uuid4()),
                claim_id=claim.id,
                corrected_text=correction.corrected_text,
                abstained=correction.abstained,
                abstain_reason=correction.abstain_reason,
                citations=[c.model_dump(mode="json") for c in correction.citations],
                max_supportable_confidence=correction.max_supportable_confidence,
            )
        )
    session.commit()


def finish_run(
    session: Session, run_id: str, annotated_text: str, provenance: RunProvenance
) -> None:
    row = session.get(RunRow, run_id)
    if row is None:
        raise RunNotFoundError(f"run {run_id} not found")
    row.annotated_text = annotated_text
    row.provenance = provenance.model_dump(mode="json")
    row.status = RunStatus.DONE.value
    session.commit()


def _claim_from_row(row: ClaimRow) -> Claim:
    from verifact.contracts import Entity, NumericRef, TemporalRef

    mentions = row.mentions or {}
    return Claim(
        id=row.id,
        sentence_idx=row.sentence_idx,
        char_start=row.char_start,
        char_end=row.char_end,
        text=row.text,
        claim_type=ClaimType(row.claim_type),
        entities=[Entity(**e) for e in mentions.get("entities", [])],
        temporal=[TemporalRef(**t) for t in mentions.get("temporal", [])],
        numerics=[NumericRef(**n) for n in mentions.get("numerics", [])],
        checkworthy=row.checkworthy,
        standalone_interpretable=row.standalone_interpretable,
    )


def load_run(session: Session, run_id: str) -> AnalysisRun:
    """Rebuild a full `AnalysisRun`, including partial results for a running job.

    Raises:
        RunNotFoundError: no such run.
    """
    stmt = (
        select(RunRow)
        .where(RunRow.id == run_id)
        .options(
            selectinload(RunRow.claims).selectinload(ClaimRow.passages),
            selectinload(RunRow.claims).selectinload(ClaimRow.verdict),
            selectinload(RunRow.claims).selectinload(ClaimRow.correction),
        )
    )
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise RunNotFoundError(f"run {run_id} not found")

    claims: list[Claim] = []
    verdicts: list[Verdict] = []
    corrections: list[Correction] = []
    passages: list[EvidencePassage] = []

    for claim_row in sorted(row.claims, key=lambda c: (c.sentence_idx, c.char_start)):
        claims.append(_claim_from_row(claim_row))
        for passage_row in claim_row.passages:
            passages.append(
                EvidencePassage(
                    id=passage_row.id,
                    claim_id=passage_row.claim_id,
                    text=passage_row.text,
                    source_id=passage_row.source_id,
                    url=passage_row.url,
                    title=passage_row.title,
                    published_at=passage_row.published_at,
                    scores=RetrievalScores(**(passage_row.scores or {})),
                )
            )
        if claim_row.verdict is not None:
            v = claim_row.verdict
            verdicts.append(
                Verdict(
                    claim_id=v.claim_id,
                    status=v.status,  # type: ignore[arg-type]
                    confidence=v.confidence,
                    calibrated=v.calibrated,
                    component_scores=v.component_scores or {},  # type: ignore[arg-type]
                    kg_check=KGCheck(**v.kg_check) if v.kg_check else None,
                    evidence_for=list(v.evidence_for or []),
                    evidence_against=list(v.evidence_against or []),
                    explanation=v.explanation,
                    budget_spent=v.budget_spent,
                    error=v.error,
                )
            )
        if claim_row.correction is not None:
            c = claim_row.correction
            corrections.append(
                Correction(
                    claim_id=c.claim_id,
                    corrected_text=c.corrected_text,
                    abstained=c.abstained,
                    abstain_reason=c.abstain_reason,
                    citations=c.citations or [],  # type: ignore[arg-type]
                    max_supportable_confidence=c.max_supportable_confidence,
                )
            )

    document = Document(
        id=row.id,
        raw_text=row.raw_text,
        normalized_text=row.normalized_text,
        sentences=[],
        asof=row.asof,
    )
    return AnalysisRun(
        id=row.id,
        status=RunStatus(row.status),
        document=document,
        claims=claims,
        verdicts=verdicts,
        corrections=corrections,
        passages=passages,
        annotated_text=row.annotated_text,
        provenance=RunProvenance(**row.provenance) if row.provenance else None,
        created_at=row.created_at,
    )


def save_feedback(
    session: Session, run_id: str, verdict_id: str | None, label: str, comment: str | None
) -> str:
    if session.get(RunRow, run_id) is None:
        raise RunNotFoundError(f"run {run_id} not found")
    row = FeedbackRow(
        id=str(uuid.uuid4()),
        run_id=run_id,
        verdict_id=verdict_id,
        label=label,
        comment=comment,
    )
    session.add(row)
    session.commit()
    return str(row.id)


def sweep_stale_runs(session: Session, older_than: datetime) -> int:
    """Mark interrupted runs failed.

    ADR-004 is explicit that a background task killed by a restart is not
    retried. Without this sweep such a run would stay `running` for ever and the
    API would keep reporting work that nothing is doing.
    """
    stmt = select(RunRow).where(
        RunRow.status == RunStatus.RUNNING.value, RunRow.updated_at < older_than
    )
    stale = list(session.execute(stmt).scalars())
    for row in stale:
        row.status = RunStatus.FAILED.value
        row.error = "run was interrupted before completion (process restart)"
    if stale:
        session.commit()
        _log.warning("marked stale runs failed", extra={"n": len(stale)})
    return len(stale)


__all__ = [
    "create_run",
    "finish_run",
    "load_run",
    "save_claim_result",
    "save_feedback",
    "set_run_status",
    "sweep_stale_runs",
]
