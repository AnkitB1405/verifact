"""Request and response schemas for the HTTP API.

Owner: P1. Kept separate from `verifact.contracts`: the contracts are the
pipeline's internal vocabulary and may change freely behind an ADR, while these
are a published interface with a version in its URL. Collapsing the two would
make every internal refactor a breaking API change.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from verifact.contracts import (
    AnalysisRun,
    Claim,
    Correction,
    EvidencePassage,
    RunStatus,
    Verdict,
)


class Strict(BaseModel):
    """Reject unknown fields so a typo in a client payload is an error."""

    model_config = ConfigDict(extra="forbid")


class AnalyzeRequest(Strict):
    text: Annotated[str, Field(min_length=1, description="AI-generated text to analyse")]
    asof: date | None = Field(
        default=None,
        description=(
            "Date the text is treated as speaking about. Temporal claims are judged "
            "against this horizon rather than against today."
        ),
    )


class AnalyzeAccepted(Strict):
    run_id: str
    status: RunStatus
    poll: str = Field(description="URL to poll for results")


class VerifyRequest(Strict):
    claim: Annotated[str, Field(min_length=1, description="A single claim to verify")]
    asof: date | None = None


class VerifyResponse(Strict):
    claim: Claim
    verdict: Verdict
    passages: list[EvidencePassage]
    explanation: str
    #: Restates in words whether the confidence may be read as a probability.
    confidence_note: str


class CorrectRequest(Strict):
    claim: Annotated[str, Field(min_length=1)]
    asof: date | None = None


class CorrectResponse(Strict):
    claim: Claim
    verdict: Verdict
    correction: Correction
    explanation: str


class FeedbackRequest(Strict):
    run_id: str
    verdict_id: str | None = None
    label: Annotated[str, Field(max_length=32, description="e.g. agree, disagree, unclear")]
    comment: Annotated[str | None, Field(default=None, max_length=2000)] = None


class FeedbackResponse(Strict):
    feedback_id: str


class ComponentHealth(Strict):
    name: str
    ok: bool
    detail: str


class HealthResponse(Strict):
    status: str
    version: str
    config_hash: str
    components: list[ComponentHealth]
    model_versions: dict[str, str]


class ResultsResponse(Strict):
    """A run, including partial results while it is still running."""

    run: AnalysisRun
    status_counts: dict[str, int]
    #: True while claims are still being processed, so a client knows to re-poll.
    partial: bool


class ErrorResponse(Strict):
    """The only error shape the API returns.

    No traceback and no echo of the submitted text (FR-52, SR-06): the input is
    the user's content and an error page is not the place for it.
    """

    code: str
    message: str
    request_id: str | None = None


class ExportedReport(Strict):
    """Re-importable verification report (FR-59)."""

    exported_at: datetime
    run: AnalysisRun
    status_counts: dict[str, int]
    meta: dict[str, Any] = Field(default_factory=dict)
