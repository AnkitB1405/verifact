"""Shared data contracts.

Every module consumes and produces these types and nothing else. A change here
is a contract change: it needs a PR approved by P1 plus the affected owner, an
entry in CHANGELOG.md, and regeneration of the golden fixture that the producing
module owns (see docs/phase-0/04-work-division.md).
"""

from verifact.contracts.models import (
    AnalysisRun,
    Citation,
    Claim,
    ClaimType,
    ComponentScores,
    Correction,
    Document,
    Entity,
    EvidencePassage,
    KGCheck,
    KGStatus,
    NumericRef,
    Probability,
    RetrievalScores,
    RunProvenance,
    RunStatus,
    Sentence,
    Source,
    SourceKind,
    TemporalRef,
    Triple,
    Verdict,
    VerdictStatus,
)

__all__ = [
    "AnalysisRun",
    "Citation",
    "Claim",
    "ClaimType",
    "ComponentScores",
    "Correction",
    "Document",
    "Entity",
    "EvidencePassage",
    "KGCheck",
    "KGStatus",
    "NumericRef",
    "Probability",
    "RetrievalScores",
    "RunProvenance",
    "RunStatus",
    "Sentence",
    "Source",
    "SourceKind",
    "TemporalRef",
    "Triple",
    "Verdict",
    "VerdictStatus",
]
