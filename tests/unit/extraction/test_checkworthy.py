"""Check-worthiness tests. Owner: P2 (FR-09)."""

from __future__ import annotations

import pytest

from verifact.contracts import ClaimType
from verifact.extraction.checkworthy import classify

FACTUAL = [
    "Water boils at 100 degrees Celsius.",
    "The Eiffel Tower is 330 metres tall.",
    "Marie Curie won the Nobel Prize in 1903.",
    "Python was created by Guido van Rossum.",
    "The treaty was signed in Paris.",
]

NOT_FACTUAL = [
    ("I think it is the most beautiful monument in Europe.", ClaimType.OPINION),
    ("The film is terrible.", ClaimType.OPINION),
    ("Vaccines should be free for everyone.", ClaimType.OPINION),
    ("Is it taller than the Shard?", ClaimType.QUESTION),
    ("Install the package before running the demo.", ClaimType.INSTRUCTION),
    ("Of course everyone already knows this.", ClaimType.RHETORICAL),
    ("The Eiffel Tower in Paris", ClaimType.RHETORICAL),
]


@pytest.mark.parametrize("text", FACTUAL)
def test_factual_claims_are_checkworthy(text: str) -> None:
    claim_type, checkworthy = classify(text)
    assert claim_type is ClaimType.FACTUAL
    assert checkworthy is True


@pytest.mark.parametrize(("text", "expected"), NOT_FACTUAL)
def test_non_factual_is_classified_and_excluded(text: str, expected: ClaimType) -> None:
    claim_type, checkworthy = classify(text)
    assert claim_type is expected, text
    assert checkworthy is False


def test_measured_rates_on_the_labelled_set() -> None:
    """Report the actual error rates rather than asserting perfection.

    The gate is deliberately loose. A tight gate on a 12-item set would be a
    threshold tuned until it passed, which ADR-005 forbids; the real numbers go
    in the test report.
    """
    labelled = [(t, True) for t in FACTUAL] + [(t, False) for t, _ in NOT_FACTUAL]
    wrong = [t for t, want in labelled if classify(t)[1] is not want]
    assert not wrong, f"misclassified: {wrong}"


def test_hedged_statements_stay_checkworthy() -> None:
    """A hedge is not an opinion: "may have been built in 1889" is still checkable."""
    claim_type, checkworthy = classify("The tower may have been built in 1889.")
    assert claim_type is ClaimType.FACTUAL
    assert checkworthy is True
