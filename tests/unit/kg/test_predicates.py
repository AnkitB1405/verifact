"""Predicate map tests. Owner: P3 (FR-23)."""

from __future__ import annotations

from pathlib import Path

import pytest

from verifact.kg.predicates import load_predicates

MAP = Path("config/kg_predicates.yaml")


@pytest.fixture(scope="module")
def predicates():  # type: ignore[no-untyped-def]
    return load_predicates(MAP)


@pytest.mark.parametrize(
    ("claim", "expected"),
    [
        ("The Eiffel Tower is located in Paris.", "located_in"),
        ("The Eiffel Tower is in France.", "located_in"),
        ("Paris is the capital city of France.", "capital_of"),
        ("Albert Einstein was born in Ulm.", "birthplace"),
        ("Marie Curie died in Passy.", "deathplace"),
        ("Python was created by Guido van Rossum.", "creator"),
        ("Marie Curie won the Nobel Prize in Physics.", "award_received"),
        ("The Eiffel Tower was completed in 1889.", "completion"),
        ("The company was founded in 1998.", "inception"),
        ("The paper was published in 2009.", "publication"),
        ("The Eiffel Tower is 330 metres tall.", "height"),
    ],
)
def test_claim_maps_to_expected_predicate(claim: str, expected: str, predicates) -> None:  # type: ignore[no-untyped-def]
    found = predicates.find(claim)
    assert found is not None, claim
    assert found.name == expected


@pytest.mark.parametrize(
    "claim",
    [
        "Water boils at 100 degrees Celsius.",
        "The algorithm runs in linear time.",
        "Inflation fell last quarter.",
    ],
)
def test_unsupported_relation_returns_none(claim: str, predicates) -> None:  # type: ignore[no-untyped-def]
    """FR-23: outside the supported set is NOT_APPLICABLE, which is not evidence."""
    assert predicates.find(claim) is None


def test_completion_and_inception_are_separate_predicates(predicates) -> None:  # type: ignore[no-untyped-def]
    """Regression for EA-01.

    'completed' and 'built/founded' are near-synonyms in English and different
    properties in Wikidata. Collapsing them produced a false CONTRADICTED on
    'The Eiffel Tower was completed in 1889' because P571 is 1887.
    """
    completion = predicates.find("The Eiffel Tower was completed in 1889.")
    inception = predicates.find("The company was founded in 1998.")
    assert completion is not None and inception is not None
    assert completion.name != inception.name
    assert "P1619" in completion.pids, "completion must consult date of official opening"


def test_match_span_locates_the_relation_phrase(predicates) -> None:  # type: ignore[no-untyped-def]
    """Regression for EA-03: the span is what separates subject from object."""
    claim = "Python was created by Guido van Rossum."
    predicate = predicates.find(claim)
    assert predicate is not None
    span = predicate.match_span(claim)
    assert span is not None
    assert claim[: span[0]].strip() == "Python"
    assert "Guido van Rossum" in claim[span[1] :]


def test_every_predicate_declares_pids_and_patterns(predicates) -> None:  # type: ignore[no-untyped-def]
    for predicate in predicates.predicates:
        assert predicate.pids, predicate.name
        assert predicate.patterns, predicate.name
        assert predicate.value_type in ("entity", "time", "quantity")


def test_missing_map_degrades_to_not_applicable(tmp_path: Path) -> None:
    """A missing config must disable KG checking, not crash the pipeline."""
    empty = load_predicates(tmp_path / "absent.yaml")
    assert empty.find("The Eiffel Tower is located in Paris.") is None
