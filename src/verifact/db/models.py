"""ORM models.

Shape follows docs/architecture/system-architecture.md §7. Fixed-shape data is
relational; the score bag and provenance are JSON, because they are only ever
read as a whole and their shape grows during the project — a column per
component score would mean a migration every time a signal is added.

`JSONB` is used on PostgreSQL and plain `JSON` on SQLite, so a clone runs with
no services while production keeps JSONB's indexing and operators.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

#: JSONB on PostgreSQL, JSON elsewhere.
JsonCol = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(32))
    reliability_tier: Mapped[int] = mapped_column(Integer)
    base_reliability: Mapped[float] = mapped_column(Float)
    halflife_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    asof: Mapped[date | None] = mapped_column(Date, nullable=True)
    annotated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: config hash, model versions, seed, stage timings (FR-62)
    provenance: Mapped[dict[str, Any]] = mapped_column(JsonCol, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    claims: Mapped[list[ClaimRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    feedback: Mapped[list[FeedbackRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ClaimRow(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    sentence_idx: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(16), default="factual")
    checkworthy: Mapped[bool] = mapped_column(Boolean, default=True)
    standalone_interpretable: Mapped[bool] = mapped_column(Boolean, default=True)
    #: entities, temporal refs and numeric refs with their spans
    mentions: Mapped[dict[str, Any]] = mapped_column(JsonCol, default=dict)

    run: Mapped[RunRow] = relationship(back_populates="claims")
    passages: Mapped[list[PassageRow]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    verdict: Mapped[VerdictRow | None] = relationship(
        back_populates="claim", cascade="all, delete-orphan", uselist=False
    )
    correction: Mapped[CorrectionRow | None] = relationship(
        back_populates="claim", cascade="all, delete-orphan", uselist=False
    )


class PassageRow(Base):
    __tablename__ = "evidence_passages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    scores: Mapped[dict[str, Any]] = mapped_column(JsonCol, default=dict)

    claim: Mapped[ClaimRow] = relationship(back_populates="passages")


class VerdictRow(Base):
    __tablename__ = "verdicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), index=True, unique=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    #: False means the confidence is a raw score, not a probability (ADR-005).
    calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    component_scores: Mapped[dict[str, Any]] = mapped_column(JsonCol, default=dict)
    kg_check: Mapped[dict[str, Any] | None] = mapped_column(JsonCol, nullable=True)
    evidence_for: Mapped[list[str]] = mapped_column(JsonCol, default=list)
    evidence_against: Mapped[list[str]] = mapped_column(JsonCol, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    budget_spent: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    claim: Mapped[ClaimRow] = relationship(back_populates="verdict")


class CorrectionRow(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), index=True, unique=True
    )
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstained: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    abstain_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JsonCol, default=list)
    max_supportable_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    claim: Mapped[ClaimRow] = relationship(back_populates="correction")


class FeedbackRow(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    #: Nullable: feedback may be about the run as a whole.
    verdict_id: Mapped[str | None] = mapped_column(
        ForeignKey("verdicts.id", ondelete="SET NULL"), nullable=True
    )
    label: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[RunRow] = relationship(back_populates="feedback")


# Verdict status is the field the dashboard and the evaluation filter on most.
Index("ix_verdicts_status_conf", VerdictRow.status, VerdictRow.confidence)
