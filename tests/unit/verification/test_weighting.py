"""Weighting stage tests. Owner: P4 (FR-28, FR-34).

This stage carries the novelty claim, so its behaviour is pinned precisely.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from verifact.retrieval.registry import load_registry
from verifact.verification.weighting import (
    cross_source_agreement,
    deduplicate,
    recency_factor,
    weigh,
)

from .conftest import ASOF, passage, weighted

REGISTRY = load_registry(Path("config/sources.yaml"))


def test_recency_halves_at_the_halflife() -> None:
    factor, undated = recency_factor(date(2023, 11, 2), 1095, ASOF)
    assert factor == pytest.approx(0.5, abs=0.01)
    assert undated is False


def test_recency_of_a_fresh_source_is_near_one() -> None:
    factor, _ = recency_factor(ASOF, 1095, ASOF)
    assert factor == pytest.approx(1.0)


def test_undated_passage_is_not_penalised() -> None:
    """A gap in a source's metadata is not evidence about the claim.

    Penalising undated passages would systematically down-weight sources with
    sparse bookkeeping, which has nothing to do with whether the claim is true.
    """
    factor, undated = recency_factor(None, 1095, ASOF)
    assert factor == 1.0
    assert undated is True


def test_undated_passage_is_never_assumed_recent_silently() -> None:
    _, undated = recency_factor(None, 1095, ASOF)
    assert undated is True, "the assumption must be recorded so it can be explained"


def test_no_halflife_means_no_decay() -> None:
    """Crossref publication metadata does not become less true with age."""
    factor, _ = recency_factor(date(1990, 1, 1), None, ASOF)
    assert factor == 1.0


def test_weight_is_the_product_of_three_factors() -> None:
    p = passage(source_id="wikipedia", relevance=0.5, published=ASOF)
    [wp] = weigh([p], REGISTRY, ASOF)
    assert wp.weight == pytest.approx(wp.reliability * wp.recency * wp.relevance)


def test_more_reliable_and_fresher_source_outweighs_a_worse_one() -> None:
    fresh_good = passage(
        text="alpha beta gamma delta", source_id="wikidata", relevance=1.0, published=ASOF
    )
    stale_poor = passage(
        text="epsilon zeta eta theta",
        source_id="local_corpus",
        relevance=1.0,
        published=date(2015, 1, 1),
    )
    results = weigh([fresh_good, stale_poor], REGISTRY, ASOF)
    assert results[0].weight > results[1].weight


def test_zero_relevance_gives_zero_weight() -> None:
    [wp] = weigh([passage(relevance=0.0, published=ASOF)], REGISTRY, ASOF)
    assert wp.weight == 0.0


def test_duplicates_are_collapsed() -> None:
    """FR-34: two mirrors of one article are one piece of evidence.

    Counting them twice would overstate cross-source agreement - the error
    kuhn2023semantic identifies when sequences rather than meanings are counted.
    """
    text = "The Eiffel Tower is 330 metres tall and stands in Paris, France."
    kept = deduplicate(
        [passage(text=text), passage(text=text), passage(text="something else entirely here")]
    )
    assert len(kept) == 2
    assert kept[0][1], "the collapsed passage id must be recorded, not discarded"


def test_distinct_passages_are_not_collapsed() -> None:
    kept = deduplicate([passage(text="alpha beta gamma"), passage(text="delta epsilon zeta")])
    assert len(kept) == 2


def test_agreement_is_counted_per_source_not_per_passage() -> None:
    """Six paragraphs from one article are one source agreeing, not six."""
    same_source = [
        weighted(source_id="wikipedia", text=f"passage number {i} unique words") for i in range(3)
    ]
    agreement = cross_source_agreement(same_source, [0.9, 0.9, 0.9])
    assert agreement == pytest.approx(1.0)

    mixed = [weighted(source_id="wikipedia"), weighted(source_id="crossref")]
    assert cross_source_agreement(mixed, [0.9, 0.1]) == pytest.approx(0.5)


def test_agreement_of_no_evidence_is_zero() -> None:
    assert cross_source_agreement([], []) == 0.0
