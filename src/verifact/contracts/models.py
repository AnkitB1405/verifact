"""Pydantic models shared by every module.

Design rules enforced here:

* Verdict statuses are an enum generated from docs/requirements/verification-statuses.md.
  Adding one is a documentation change first.
* ComponentScores keeps every signal separately. Nothing in this file collapses
  the signals into a single opaque number (brief §3.F, FR-31).
* `Verdict.calibrated` is set by the calibration stage from whether a fitted
  calibrator actually loaded. A caller cannot claim calibration it does not have
  (ADR-005), which is why the aggregation stage constructs Verdicts with
  calibrated=False and only `verification.calibrate` may set it True.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Probability = Annotated[float, Field(ge=0.0, le=1.0)]


def _new_id() -> str:
    return str(uuid.uuid4())


class Frozen(BaseModel):
    """Immutable base. Pipeline stages produce new objects instead of mutating."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerdictStatus(StrEnum):
    """The six statuses. See docs/requirements/verification-statuses.md."""

    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIABLE = "UNVERIFIABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    OUTDATED = "OUTDATED"
    AMBIGUOUS = "AMBIGUOUS"


class KGStatus(StrEnum):
    """Knowledge-graph outcome.

    MISSING means the graph does not hold the relation. It is *silence*, not
    denial, and the aggregation rule must never turn it into CONTRADICTED
    (FR-24; the limitation identified in shiralkar2017streams).
    """

    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SourceKind(StrEnum):
    ENCYCLOPAEDIA = "encyclopaedia"
    KNOWLEDGE_BASE = "knowledge_base"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    NEWS = "news"
    LOCAL_CORPUS = "local_corpus"
    UNKNOWN = "unknown"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ClaimType(StrEnum):
    FACTUAL = "factual"
    OPINION = "opinion"
    INSTRUCTION = "instruction"
    QUESTION = "question"
    RHETORICAL = "rhetorical"


# --------------------------------------------------------------------------- input


class Sentence(Frozen):
    idx: int = Field(ge=0)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    text: str

    @model_validator(mode="after")
    def _span_is_ordered(self) -> Sentence:
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be greater than char_start")
        return self


class Document(Frozen):
    id: str = Field(default_factory=_new_id)
    raw_text: str
    normalized_text: str
    sentences: list[Sentence] = Field(default_factory=list)
    #: The date the input text is treated as speaking about. Temporal claims are
    #: judged against this horizon rather than against "now" (FR-06).
    asof: date | None = None


# ----------------------------------------------------------------------- extraction


class Entity(Frozen):
    surface: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    label: str
    #: Knowledge-base id (e.g. a Wikidata QID), or None when unresolved.
    kb_id: str | None = None
    kb_confidence: Probability | None = None
    #: Populated when the mention is ambiguous: never silently pick one (FR-21).
    kb_candidates: list[str] = Field(default_factory=list)


class TemporalRef(Frozen):
    surface: str
    #: ISO-8601 where parseable, else None with the surface form kept.
    iso: str | None = None
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class NumericRef(Frozen):
    surface: str
    value: float | None = None
    unit: str | None = None
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class Claim(Frozen):
    id: str = Field(default_factory=_new_id)
    sentence_idx: int = Field(ge=0)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    text: str
    claim_type: ClaimType = ClaimType.FACTUAL
    entities: list[Entity] = Field(default_factory=list)
    temporal: list[TemporalRef] = Field(default_factory=list)
    numerics: list[NumericRef] = Field(default_factory=list)
    checkworthy: bool = True
    #: False when the claim contains an unresolved referent. Such a claim routes
    #: to AMBIGUOUS rather than receiving a guessed verdict (FR-11).
    standalone_interpretable: bool = True


# ------------------------------------------------------------------------ retrieval


class Source(Frozen):
    id: str
    name: str
    kind: SourceKind
    #: 1 = most reliable. An unregistered source gets the lowest tier, never
    #: silent rejection (FR-14).
    reliability_tier: int = Field(ge=1, le=5)
    base_reliability: Probability
    #: Recency half-life in days for this kind of source. None = do not decay.
    halflife_days: int | None = None


class RetrievalScores(Frozen):
    bm25: float | None = None
    dense: float | None = None
    rrf: float = 0.0
    #: RRF scaled to [0,1] within one claim's candidate set, for use as a weight.
    relevance: Probability = 0.0


class EvidencePassage(Frozen):
    id: str = Field(default_factory=_new_id)
    claim_id: str
    text: str
    source_id: str
    url: str | None = None
    title: str | None = None
    #: None when the source gives no date. Treated as non-decaying and recorded
    #: as undated; never assumed to be recent.
    published_at: date | None = None
    scores: RetrievalScores = RetrievalScores()


# ------------------------------------------------------------------- knowledge graph


class Triple(Frozen):
    subject: str
    predicate: str
    object: str
    subject_qid: str | None = None
    object_qid: str | None = None


class KGCheck(Frozen):
    claim_id: str
    status: KGStatus = KGStatus.NOT_APPLICABLE
    triples_checked: list[Triple] = Field(default_factory=list)
    #: The graph path that produced the outcome, so the decision is inspectable (FR-25).
    path_evidence: list[list[str]] = Field(default_factory=list)
    notes: str | None = None


# ----------------------------------------------------------------------- verification


class ComponentScores(Frozen):
    """Every signal, kept separately and never collapsed (FR-31)."""

    similarity_max: Probability = 0.0
    similarity_mean: Probability = 0.0
    nli_entail: Probability = 0.0
    nli_contra: Probability = 0.0
    nli_neutral: Probability = 0.0
    source_reliability: Probability = 0.0
    recency: Probability = 0.0
    cross_source_agreement: Probability = 0.0
    kg_consistency: float = 0.0
    evidence_coverage: Probability = 0.0
    #: Weighted entailment and contradiction from the aggregation formula.
    weighted_entail: Probability = 0.0
    weighted_contra: Probability = 0.0


class Verdict(Frozen):
    claim_id: str
    status: VerdictStatus
    #: Calibrated when `calibrated` is True; otherwise a raw, uncalibrated score
    #: that must not be presented as a probability (ADR-005).
    confidence: Probability
    calibrated: bool = False
    component_scores: ComponentScores = ComponentScores()
    kg_check: KGCheck | None = None
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    explanation: str = ""
    #: Number of passages retrieved plus escalation steps taken, for the H2
    #: cost/accuracy curve.
    budget_spent: int = 0
    #: Set when this one claim failed; the rest of the run still completes.
    error: str | None = None


# ------------------------------------------------------------------------ mitigation


class Citation(Frozen):
    passage_id: str
    source_id: str
    url: str | None = None


class Correction(Frozen):
    claim_id: str
    corrected_text: str | None = None
    abstained: bool = False
    abstain_reason: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    #: A correction may never be more confident than the evidence behind it (FR-40).
    max_supportable_confidence: Probability = 0.0

    @model_validator(mode="after")
    def _abstention_is_consistent(self) -> Correction:
        if self.abstained and self.corrected_text is not None:
            raise ValueError("an abstained correction must not carry corrected_text")
        if not self.abstained and self.corrected_text is None:
            raise ValueError("a non-abstained correction must carry corrected_text")
        if self.abstained and not self.abstain_reason:
            raise ValueError("abstention must record a reason")
        if not self.abstained and not self.citations:
            raise ValueError("a correction must cite at least one passage (FR-37)")
        return self


# ------------------------------------------------------------------------------ run


class RunProvenance(Frozen):
    """What produced this run. Without it a result is not reproducible (FR-62)."""

    config_hash: str
    model_versions: dict[str, str] = Field(default_factory=dict)
    seed: int | None = None
    timings_ms: dict[str, float] = Field(default_factory=dict)


class AnalysisRun(Frozen):
    id: str = Field(default_factory=_new_id)
    status: RunStatus = RunStatus.QUEUED
    document: Document
    claims: list[Claim] = Field(default_factory=list)
    verdicts: list[Verdict] = Field(default_factory=list)
    corrections: list[Correction] = Field(default_factory=list)
    passages: list[EvidencePassage] = Field(default_factory=list)
    annotated_text: str | None = None
    provenance: RunProvenance | None = None
    created_at: datetime | None = None
