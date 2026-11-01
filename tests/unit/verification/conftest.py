"""Builders for aggregation tests. Owner: P4.

Everything here is constructed in memory so the status rule is tested
independently of retrieval, models and the network. The golden fixtures from P3
are used where real evidence shapes matter.
"""

from __future__ import annotations

from datetime import date

import pytest

from verifact.contracts import (
    Claim,
    EvidencePassage,
    KGCheck,
    KGStatus,
    RetrievalScores,
)
from verifact.verification.nli import NliResult
from verifact.verification.weighting import WeightedPassage

ASOF = date(2026, 11, 1)
#: Lower number is more reliable, matching config/sources.yaml.
TIERS = {"wikidata": 1, "wikipedia": 2, "crossref": 3, "local_corpus": 4, "unknown": 5}


@pytest.fixture
def claim() -> Claim:
    text = "The Eiffel Tower is located in Paris."
    return Claim(sentence_idx=0, char_start=0, char_end=len(text), text=text)


def passage(
    text: str = "evidence text",
    source_id: str = "wikipedia",
    relevance: float = 1.0,
    published: date | None = None,
) -> EvidencePassage:
    return EvidencePassage(
        claim_id="c1",
        text=text,
        source_id=source_id,
        published_at=published,
        scores=RetrievalScores(relevance=relevance, rrf=relevance),
    )


def weighted(
    weight: float = 0.75,
    source_id: str = "wikipedia",
    published: date | None = None,
    text: str = "evidence text",
) -> WeightedPassage:
    return WeightedPassage(
        passage=passage(text=text, source_id=source_id, published=published),
        reliability=0.75,
        recency=1.0,
        relevance=1.0,
        weight=weight,
        undated=published is None,
    )


def nli(entail: float = 0.0, contra: float = 0.0, neutral: float | None = None) -> NliResult:
    if neutral is None:
        neutral = max(0.0, 1.0 - entail - contra)
    return NliResult(entail, contra, neutral, "test")


def kg(status: KGStatus) -> KGCheck:
    return KGCheck(claim_id="c1", status=status, notes=f"test {status.value}")
