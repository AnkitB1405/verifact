"""Decomposition tests. Owner: P2.

The five worked examples in ADR-002 are the contract for what "atomic" means.
They are asserted here so a change to the decomposer that breaks the published
definition fails CI rather than quietly changing the project's semantics.
"""

from __future__ import annotations

import pytest

from verifact.extraction.decompose import decompose, is_standalone_interpretable


@pytest.fixture(scope="module")
def nlp():  # type: ignore[no-untyped-def]
    spacy = pytest.importorskip("spacy")
    try:
        return spacy.load("en_core_web_sm", exclude=["lemmatizer", "textcat"])
    except OSError:
        pytest.skip("en_core_web_sm not installed")


def _texts(nlp, sentence: str) -> list[str]:  # type: ignore[no-untyped-def]
    sent = list(nlp(sentence).sents)[0]
    return [p.text for p in decompose(sentence, 0, sent)]


@pytest.mark.ml
def test_adr002_example_1_coordinated_modifiers(nlp) -> None:  # type: ignore[no-untyped-def]
    out = _texts(
        nlp, "Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911."
    )
    assert out == [
        "Marie Curie won the Nobel Prize in Physics in 1903.",
        "Marie Curie won the Nobel Prize in Chemistry in 1911.",
    ]


@pytest.mark.ml
def test_adr002_example_2_participial_modifier(nlp) -> None:  # type: ignore[no-untyped-def]
    out = _texts(nlp, "The Eiffel Tower, completed in 1889, is 330 metres tall.")
    assert out == [
        "The Eiffel Tower was completed in 1889.",
        "The Eiffel Tower is 330 metres tall.",
    ]


@pytest.mark.ml
def test_relative_clause_is_extracted(nlp) -> None:  # type: ignore[no-untyped-def]
    out = _texts(nlp, "Albert Einstein, who was born in Ulm, developed the theory of relativity.")
    assert out == [
        "Albert Einstein was born in Ulm.",
        "Albert Einstein developed the theory of relativity.",
    ]


@pytest.mark.ml
def test_clausal_coordination_splits_and_drops_the_coordinator(nlp) -> None:  # type: ignore[no-untyped-def]
    out = _texts(nlp, "Python was created by Guido van Rossum and it is maintained by the PSF.")
    assert out == [
        "Python was created by Guido van Rossum.",
        "It is maintained by the PSF.",
    ]
    assert not any(t.rstrip(".").endswith(" and") for t in out)


@pytest.mark.ml
def test_simple_sentence_is_left_alone(nlp) -> None:  # type: ignore[no-untyped-def]
    assert _texts(nlp, "Water boils at 100 degrees Celsius.") == [
        "Water boils at 100 degrees Celsius."
    ]


@pytest.mark.ml
def test_documented_limitation_multiple_coordinators_not_split(nlp) -> None:  # type: ignore[no-untyped-def]
    """ADR-002 limitation: more than one coordinator is left as a single claim.

    Asserted so the limitation is a measured fact in the test report rather than
    a vague caveat, and so implementing it later is a visible change.
    """
    sentence = "The summit was held in Paris in 2015 and in Glasgow in 2021 and in Dubai in 2023."
    assert len(_texts(nlp, sentence)) == 1


@pytest.mark.ml
def test_spans_point_into_the_source_text(nlp) -> None:  # type: ignore[no-untyped-def]
    sentence = "The Eiffel Tower, completed in 1889, is 330 metres tall."
    for prop in decompose(sentence, 0, list(nlp(sentence).sents)[0]):
        assert 0 <= prop.char_start < prop.char_end <= len(sentence)


@pytest.mark.parametrize(
    ("text", "interpretable"),
    [
        ("Marie Curie won the prize.", True),
        ("He later moved to Berlin.", False),
        ("It is maintained by the PSF.", False),
        ("They founded the company in 1998.", False),
        ("In 1999, he joined CERN.", False),
        ("This changed everything.", False),
        ("Water boils at 100 degrees Celsius.", True),
    ],
)
def test_standalone_interpretability(text: str, interpretable: bool) -> None:
    """FR-11: an unresolved referent is flagged, never guessed."""
    assert is_standalone_interpretable(text) is interpretable


def test_regex_fallback_splits_on_semicolon() -> None:
    """The dependency-free path still has to produce something sane."""
    out = [p.text for p in decompose("Paris is in France; Berlin is in Germany.", 0, None)]
    assert out == ["Paris is in France.", "Berlin is in Germany."]


def test_regex_fallback_spans_are_within_the_sentence() -> None:
    sentence = "Paris is in France; Berlin is in Germany."
    for prop in decompose(sentence, 0, None):
        assert 0 <= prop.char_start < prop.char_end <= len(sentence)
