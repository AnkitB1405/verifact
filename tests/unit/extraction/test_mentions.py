"""Mention extraction tests. Owner: P2."""

from __future__ import annotations

import pytest

from verifact.extraction.mentions import (
    extract_entities_regex,
    extract_numerics,
    extract_temporal,
)


@pytest.mark.parametrize(
    ("text", "expected_iso"),
    [
        ("Signed on 1889-03-31.", ["1889-03-31"]),
        ("Signed on 12 March 1999.", ["1999-03-12"]),
        ("Signed in March 1999.", ["1999-03"]),
        ("Built in 1889.", ["1889"]),
        ("Popular in the 1960s.", ["1960"]),
    ],
)
def test_temporal_iso_parsing(text: str, expected_iso: list[str]) -> None:
    assert [t.iso for t in extract_temporal(text)] == expected_iso


def test_temporal_spans_are_exact() -> None:
    text = "Completed in 1889 and extended in 1957."
    for ref in extract_temporal(text):
        assert text[ref.char_start : ref.char_end] == ref.surface


def test_years_are_not_reported_as_quantities() -> None:
    """A year is temporal, not a measurement; counting it twice skews weighting."""
    nums = extract_numerics("By 1990 the tower drew more visitors.")
    assert nums == []


def test_decade_is_not_parsed_as_seconds() -> None:
    """'1960s' must not become 1960 seconds - the unit regex would happily do that."""
    assert extract_numerics("Popular in the 1960s.") == []


@pytest.mark.parametrize(
    ("text", "value", "unit"),
    [
        ("It is 330 metres tall.", 330.0, "metres"),
        ("Attendance rose 40%.", 40.0, "%"),
        ("It cost 7.8 million francs.", 7.8, "million"),
        ("The sample weighed 1,250 kg.", 1250.0, "kg"),
        ("Water boils at 100 °C.", 100.0, "°C"),
    ],
)
def test_numeric_value_and_unit(text: str, value: float, unit: str) -> None:
    nums = extract_numerics(text)
    assert nums, text
    assert nums[0].value == value
    assert nums[0].unit == unit


def test_numeric_spans_are_exact() -> None:
    text = "It is 330 metres tall and cost 7.8 million francs."
    for ref in extract_numerics(text):
        assert text[ref.char_start : ref.char_end] == ref.surface


def test_regex_entities_strip_leading_article() -> None:
    ents = extract_entities_regex("The Eiffel Tower is tall.")
    assert [e.surface for e in ents] == ["Eiffel Tower"]
    assert all(e.label == "PROPN" for e in ents), "the fallback must not guess a type"


def test_regex_entities_skip_bare_sentence_case() -> None:
    """A lone capitalised first word is sentence case, not a proper noun."""
    assert extract_entities_regex("Water boils at 100 degrees.") == []


def test_regex_entity_connector_requires_a_following_capital() -> None:
    """'Install the package' must not yield the entity 'Install the'."""
    surfaces = [e.surface for e in extract_entities_regex("Install the package now.")]
    assert "Install the" not in surfaces
