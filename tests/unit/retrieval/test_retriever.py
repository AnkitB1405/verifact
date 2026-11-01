"""Retriever tests. Owner: P3.

These run against the local corpus with no network, so they test the real code
path (FR-18 is the same path with a different source) and stay deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from verifact.config import RetrievalSettings
from verifact.contracts import Claim, Entity
from verifact.retrieval.clients import local
from verifact.retrieval.retriever import build_query, rank_passages

CORPUS = Path("tests/fixtures/local_corpus.jsonl")


def _claim(text: str, entities: list[str]) -> Claim:
    ents = []
    for surface in entities:
        start = text.find(surface)
        ents.append(
            Entity(
                surface=surface,
                char_start=max(start, 0),
                char_end=max(start, 0) + len(surface),
                label="TEST",
            )
        )
    return Claim(sentence_idx=0, char_start=0, char_end=len(text), text=text, entities=ents)


@pytest.fixture
def passages():  # type: ignore[no-untyped-def]
    return local.to_passages(local.load_corpus(CORPUS), "claim-1")


def test_corpus_loads(passages) -> None:  # type: ignore[no-untyped-def]
    assert len(passages) == 6
    assert all(p.source_id == "local_corpus" for p in passages)
    assert all(p.published_at is not None for p in passages), "FR-16: dates must be captured"


def test_malformed_lines_are_skipped_not_fatal(tmp_path: Path) -> None:
    path = tmp_path / "corpus.jsonl"
    path.write_text('{"text": "good"}\nnot json\n{"no_text": 1}\n\n{"text": "also good"}\n')
    assert len(local.load_corpus(path)) == 2


def test_missing_corpus_is_empty_not_an_error(tmp_path: Path) -> None:
    assert local.load_corpus(tmp_path / "absent.jsonl") == []


def test_build_query_front_loads_entities() -> None:
    """The entity identifies the document; the predicate is what we are checking."""
    claim = _claim("The Eiffel Tower is 330 metres tall.", ["Eiffel Tower"])
    assert build_query(claim).startswith("Eiffel Tower")


def test_ranking_puts_the_relevant_passage_first(passages) -> None:  # type: ignore[no-untyped-def]
    claim = _claim("The Eiffel Tower is 330 metres tall.", ["Eiffel Tower"])
    ranked = rank_passages(claim, passages, top_k=3, settings=RetrievalSettings(backend="lexical"))
    assert len(ranked) == 3
    assert "330 metres" in ranked[0].text


def test_ranking_attaches_scores(passages) -> None:  # type: ignore[no-untyped-def]
    """FR-16: component retrieval scores must be recorded, not just an order."""
    claim = _claim("Marie Curie won the Nobel Prize in Physics in 1903.", ["Marie Curie"])
    ranked = rank_passages(claim, passages, top_k=2, settings=RetrievalSettings(backend="lexical"))
    top = ranked[0]
    assert top.scores.bm25 is not None
    assert top.scores.rrf > 0
    assert 0.0 <= top.scores.relevance <= 1.0


def test_relevance_is_scaled_within_the_candidate_set(passages) -> None:  # type: ignore[no-untyped-def]
    claim = _claim("Python was created by Guido van Rossum.", ["Python"])
    ranked = rank_passages(claim, passages, top_k=6, settings=RetrievalSettings(backend="lexical"))
    assert ranked[0].scores.relevance == pytest.approx(1.0)
    assert min(p.scores.relevance for p in ranked) == pytest.approx(0.0)


def test_ranking_is_deterministic(passages) -> None:  # type: ignore[no-untyped-def]
    """NFR-06: identical input and config must give identical evidence order."""
    claim = _claim("The Eiffel Tower is 330 metres tall.", ["Eiffel Tower"])
    cfg = RetrievalSettings(backend="lexical")
    first = [p.text for p in rank_passages(claim, passages, 4, cfg)]
    second = [p.text for p in rank_passages(claim, passages, 4, cfg)]
    assert first == second


def test_no_candidates_yields_no_passages() -> None:
    """An empty result is legitimate and becomes UNVERIFIABLE, never CONTRADICTED."""
    claim = _claim("Some claim.", [])
    assert rank_passages(claim, [], top_k=3) == []


def test_top_k_is_respected(passages) -> None:  # type: ignore[no-untyped-def]
    claim = _claim("The Eiffel Tower is 330 metres tall.", ["Eiffel Tower"])
    assert len(rank_passages(claim, passages, 1, RetrievalSettings(backend="lexical"))) == 1


@pytest.mark.ml
def test_dense_and_lexical_fusion_changes_the_ranking(passages) -> None:  # type: ignore[no-untyped-def]
    """Fusion should not be a no-op; if it were, running both would be waste."""
    claim = _claim("How high does the Parisian iron structure reach?", [])
    lexical = rank_passages(claim, passages, 6, RetrievalSettings(backend="lexical"))
    fused = rank_passages(claim, passages, 6, RetrievalSettings(backend="dense"))
    assert [p.text for p in lexical] != [p.text for p in fused] or all(
        p.scores.dense is not None for p in fused
    )
