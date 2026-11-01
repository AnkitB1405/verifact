"""Ranking tests. Owner: P3."""

from __future__ import annotations

import pytest

from verifact.retrieval.rankers import (
    bm25_scores,
    dense_scores,
    minmax,
    rank_order,
    rrf,
    tokenize,
)

DOCS = [
    "The Eiffel Tower is 330 metres tall including its antenna.",
    "The Shard in London reaches 309.6 metres.",
    "Gustave Eiffel designed the tower for the 1889 World's Fair.",
    "Paris is the capital city of France.",
]


def test_tokenize_keeps_dotted_and_numeric_forms() -> None:
    """Dates and identifiers are what a factual claim turns on; stemming would ruin them."""
    assert tokenize("U.S. policy in 1990s cost $7.8 million") == [
        "u.s",
        "policy",
        "in",
        "1990s",
        "cost",
        "7.8",
        "million",
    ]


def test_bm25_ranks_the_lexically_matching_doc_first() -> None:
    scores = bm25_scores("How tall is the Eiffel Tower?", DOCS)
    assert rank_order(scores)[0] == 0


def test_bm25_scores_zero_for_no_overlap() -> None:
    assert bm25_scores("quantum chromodynamics", ["bread recipe"])[0] <= 0.0


def test_rank_order_is_deterministic_on_ties() -> None:
    """NFR-06: an unstable sort would reorder evidence between identical runs."""
    assert rank_order([1.0, 1.0, 1.0]) == [0, 1, 2]


def test_rrf_prefers_documents_ranked_well_by_both() -> None:
    # doc 1 is second in both rankings; doc 0 and 2 are first in one each.
    fused = rrf([[0, 1, 2], [2, 1, 0]], k=60, n_docs=3)
    assert fused[1] > 0
    assert abs(fused[0] - fused[2]) < 1e-12, "symmetric inputs must give symmetric scores"


def test_rrf_needs_no_score_normalisation() -> None:
    """The reason RRF was chosen: BM25 and cosine are not on a comparable scale."""
    big = rrf([[0, 1]], k=60, n_docs=2)
    same = rrf([[0, 1]], k=60, n_docs=2)
    assert big == same


def test_minmax_handles_degenerate_input() -> None:
    assert minmax([]) == []
    assert minmax([0.0, 0.0]) == [0.0, 0.0]
    assert minmax([5.0, 5.0]) == [1.0, 1.0]
    assert minmax([0.0, 1.0, 2.0]) == [0.0, 0.5, 1.0]


def test_empty_inputs_are_safe() -> None:
    assert bm25_scores("x", []) == []
    assert rrf([], k=60, n_docs=0) == []


@pytest.mark.ml
def test_dense_finds_a_paraphrase_that_bm25_misses() -> None:
    """The complementarity claim in the module docstring, measured not asserted.

    This is also the clearest demonstration of why similarity cannot be the
    verification signal: it rewards topical closeness, not entailment.
    """
    query = "How tall is the Eiffel Tower?"
    paraphrase = ["The Parisian iron lattice structure stands 330 m high."]
    lexical = bm25_scores(query, paraphrase)[0]
    semantic = dense_scores(query, paraphrase)
    assert semantic is not None, "ml marker implies the embedder is installed"
    assert lexical <= 0.0 < semantic[0]


@pytest.mark.ml
def test_similarity_cannot_tell_negation_apart() -> None:
    """Why stage S1 is not the verdict: negation barely moves cosine similarity."""
    scores = dense_scores(
        "Einstein was born in Ulm.",
        ["Einstein was born in Ulm.", "Einstein was not born in Ulm."],
    )
    assert scores is not None
    assert scores[1] > 0.8, (
        "a contradiction scores as highly similar, so similarity alone would "
        f"call it supported (got {scores[1]:.3f})"
    )
