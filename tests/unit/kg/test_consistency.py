"""Consistency-check tests. Owner: P3 (FR-24, FR-25).

The pure comparison helpers are tested without network. The live checks are
marked `network` and assert the behaviours that define the module: an absent
relation is MISSING, and transitivity reaches a true answer the direct statement
does not contain.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from verifact.contracts import KGStatus
from verifact.extraction import extract_claims
from verifact.input import build_document
from verifact.kg.consistency import (
    _compare_quantity,
    _compare_time,
    _objects_for,
    _subject_for,
    _year,
    check_claim,
)
from verifact.kg.predicates import load_predicates

PREDICATES = load_predicates(Path("config/kg_predicates.yaml"))


def _claim(text: str):  # type: ignore[no-untyped-def]
    claims = [c for c in extract_claims(build_document(text)) if c.checkworthy]
    assert claims, text
    return claims[0]


# -- pure helpers -------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [("+1889-03-31T00:00:00Z", "1889"), ("1889-03-31", "1889"), ("1889", "1889"), ("x", None)],
)
def test_year_extraction(value: str, expected: str | None) -> None:
    assert _year(value) == expected


def test_time_comparison_matches_on_year() -> None:
    values = [{"type": "time", "time": "+1889-03-31T00:00:00Z"}]
    ok, note = _compare_time(values, "1889")
    assert ok
    assert "1889" in note


def test_time_comparison_reports_what_the_graph_holds() -> None:
    """An explanation naming only 'no match' is useless to the person reading it."""
    values = [{"type": "time", "time": "+1887-01-28T00:00:00Z"}]
    ok, note = _compare_time(values, "1950")
    assert not ok
    assert "1887" in note and "1950" in note


def test_quantity_comparison_reports_the_closest_value() -> None:
    """Regression for EA-04: the explanation must name the value that justified it."""
    values = [
        {"type": "quantity", "amount": "+300"},
        {"type": "quantity", "amount": "+324"},
        {"type": "quantity", "amount": "+330"},
    ]
    ok, note = _compare_quantity(values, 330.0, 0.02)
    assert ok
    assert "+330" in note, note


def test_quantity_comparison_rejects_a_real_mismatch() -> None:
    values = [{"type": "quantity", "amount": "+330"}]
    ok, _ = _compare_quantity(values, 1000.0, 0.02)
    assert not ok


def test_subject_is_taken_before_the_relation_phrase() -> None:
    """Regression for EA-03."""
    claim = _claim("Python was created by Guido van Rossum.")
    predicate = PREDICATES.find(claim.text)
    assert predicate is not None
    subject = _subject_for(claim, predicate)
    objects = _objects_for(claim, predicate)
    assert subject is not None
    assert subject.surface == "Python"
    assert objects and "Guido" in objects[0].surface


def test_subject_selection_survives_no_recognised_entities() -> None:
    claim = _claim("The small village was founded in 1702.")
    predicate = PREDICATES.find(claim.text)
    assert predicate is not None
    subject = _subject_for(claim, predicate)
    assert subject is not None and subject.surface


# -- live checks --------------------------------------------------------------


@pytest.mark.network
def test_absent_relation_is_missing_never_contradicted() -> None:
    """FR-24, the project's defining rule for this module.

    Wikidata not holding a fact is silence. If this ever returns CONTRADICTED
    the whole system becomes a false-positive machine, which is the limitation
    identified in shiralkar2017streams.
    """
    check = check_claim(_claim("Guido van Rossum was created by Python."))
    assert check.status is not KGStatus.CONTRADICTED
    assert check.status in (KGStatus.MISSING, KGStatus.NOT_APPLICABLE)


@pytest.mark.network
def test_transitive_location_is_supported_with_a_path() -> None:
    """The reason a graph is used at all.

    Wikidata's direct P131 for the Eiffel Tower is the 7th arrondissement, not
    Paris. Checking the direct statement alone would contradict a true claim.
    """
    check = check_claim(_claim("The Eiffel Tower is located in Paris."))
    assert check.status is KGStatus.SUPPORTED
    assert check.path_evidence, "FR-25: the path is the explanation"


@pytest.mark.network
def test_false_location_is_contradicted() -> None:
    check = check_claim(_claim("The Eiffel Tower is located in Berlin."))
    assert check.status is KGStatus.CONTRADICTED


@pytest.mark.network
def test_completion_date_is_not_contradicted_by_inception() -> None:
    """Regression for EA-01: P571 is 1887, P1619 is 1889; the claim is true."""
    check = check_claim(_claim("The Eiffel Tower was completed in 1889."))
    assert check.status is KGStatus.SUPPORTED, check.notes


@pytest.mark.network
def test_wrong_date_is_contradicted() -> None:
    check = check_claim(_claim("The Eiffel Tower was completed in 1950."))
    assert check.status is KGStatus.CONTRADICTED


@pytest.mark.network
def test_unsupported_predicate_is_not_applicable() -> None:
    check = check_claim(_claim("Water boils at 100 degrees Celsius."))
    assert check.status is KGStatus.NOT_APPLICABLE
    assert "predicate" in (check.notes or "")


def test_disabled_kg_returns_not_applicable() -> None:
    from verifact.config import KGSettings

    check = check_claim(
        _claim("The Eiffel Tower is located in Paris."), settings=KGSettings(enabled=False)
    )
    assert check.status is KGStatus.NOT_APPLICABLE
