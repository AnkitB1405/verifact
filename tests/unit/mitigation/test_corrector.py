"""Correction tests. Owner: P2 (FR-37…FR-41).

Abstention is the expected outcome for most claims. These tests check that it
happens for the right reasons, and that when a correction *is* produced it is
grounded in something cited.
"""

from __future__ import annotations

import pytest

from verifact.contracts import (
    Claim,
    ComponentScores,
    EvidencePassage,
    KGCheck,
    KGStatus,
    NumericRef,
    RetrievalScores,
    TemporalRef,
    Verdict,
    VerdictStatus,
)
from verifact.mitigation import correct_claim

TEXT = "The Eiffel Tower was completed in 1950."


def _claim(text: str = TEXT, **kwargs: object) -> Claim:
    base: dict[str, object] = {
        "sentence_idx": 0,
        "char_start": 0,
        "char_end": len(text),
        "text": text,
    }
    base.update(kwargs)
    return Claim(**base)  # type: ignore[arg-type]


def _dated_claim() -> Claim:
    start = TEXT.index("1950")
    return _claim(
        temporal=[TemporalRef(surface="1950", iso="1950", char_start=start, char_end=start + 4)]
    )


def _verdict(
    status: VerdictStatus = VerdictStatus.CONTRADICTED,
    confidence: float = 0.9,
    kg_notes: str | None = "claim says 1950, graph holds ['1889']",
    evidence_against: list[str] | None = None,
) -> Verdict:
    kg = KGCheck(claim_id="c1", status=KGStatus.CONTRADICTED, notes=kg_notes) if kg_notes else None
    return Verdict(
        claim_id="c1",
        status=status,
        confidence=confidence,
        kg_check=kg,
        evidence_against=evidence_against or [],
        component_scores=ComponentScores(),
    )


def _passage(text: str, pid: str = "p1") -> EvidencePassage:
    return EvidencePassage(
        id=pid,
        claim_id="c1",
        text=text,
        source_id="wikipedia",
        url="https://en.wikipedia.org/wiki/Eiffel_Tower",
        scores=RetrievalScores(relevance=1.0),
    )


# -- abstention ---------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        VerdictStatus.SUPPORTED,
        VerdictStatus.UNVERIFIABLE,
        VerdictStatus.INSUFFICIENT_EVIDENCE,
        VerdictStatus.AMBIGUOUS,
    ],
)
def test_abstains_for_statuses_with_nothing_to_correct_from(status: VerdictStatus) -> None:
    """FR-38. UNVERIFIABLE has no replacement value available.

    Inventing one would be the fabrication this project exists to catch, so
    "I don't know" must be a first-class output.
    """
    correction = correct_claim(_dated_claim(), _verdict(status=status), [])
    assert correction.abstained is True
    assert correction.corrected_text is None
    assert correction.abstain_reason


def test_abstains_when_evidence_confidence_is_too_low() -> None:
    correction = correct_claim(_dated_claim(), _verdict(confidence=0.05), [])
    assert correction.abstained is True
    assert "below" in (correction.abstain_reason or "")


def test_abstains_when_no_replacement_value_is_available() -> None:
    """The evidence says the claim is wrong but not what the right answer is."""
    claim = _claim("The Eiffel Tower is located in Berlin.")
    correction = correct_claim(claim, _verdict(kg_notes="relation points to Q142, not Q64"), [])
    assert correction.abstained is True
    assert "replacement value" in (correction.abstain_reason or "")


def test_abstention_records_the_confidence_ceiling() -> None:
    correction = correct_claim(_dated_claim(), _verdict(confidence=0.05), [])
    assert correction.max_supportable_confidence == pytest.approx(0.05)


# -- grounded correction ------------------------------------------------------


def test_corrects_a_date_from_the_knowledge_graph() -> None:
    correction = correct_claim(_dated_claim(), _verdict(), [])
    assert correction.abstained is False
    assert correction.corrected_text == "The Eiffel Tower was completed in 1889."


def test_correction_always_carries_a_citation() -> None:
    """FR-37: a correction with no citation is an assertion, not a correction."""
    correction = correct_claim(_dated_claim(), _verdict(), [])
    assert correction.citations
    assert correction.citations[0].source_id


def test_correction_confidence_is_capped_by_its_evidence() -> None:
    """FR-40: a correction may never be more confident than what supports it."""
    correction = correct_claim(_dated_claim(), _verdict(confidence=0.55), [])
    assert correction.max_supportable_confidence == pytest.approx(0.55)


def test_corrects_a_number_and_keeps_the_unit() -> None:
    text = "The Eiffel Tower is 500 metres tall."
    start = text.index("500")
    claim = _claim(
        text,
        numerics=[
            NumericRef(
                surface="500 metres",
                value=500.0,
                unit="metres",
                char_start=start,
                char_end=start + 10,
            )
        ],
    )
    verdict = _verdict(kg_notes="claim says 500.0, graph holds ['+324', '+330']")
    correction = correct_claim(claim, verdict, [])
    assert correction.corrected_text == "The Eiffel Tower is 324 metres tall."


def test_corrects_a_date_from_a_cited_passage_when_the_graph_is_silent() -> None:
    passage = _passage("The tower was officially opened on 31 March 1889 for the Exposition.")
    verdict = _verdict(kg_notes=None, evidence_against=[passage.id])
    correction = correct_claim(_dated_claim(), verdict, [passage])
    assert correction.abstained is False
    assert "1889" in (correction.corrected_text or "")
    assert correction.citations[0].passage_id == passage.id


def test_only_the_substituted_span_changes() -> None:
    """FR-39 by construction: nothing is generated, so nothing can be invented."""
    correction = correct_claim(_dated_claim(), _verdict(), [])
    original_words = TEXT.replace("1950", "").split()
    corrected_words = (correction.corrected_text or "").replace("1889", "").split()
    assert original_words == corrected_words


def test_correction_is_deterministic() -> None:
    first = correct_claim(_dated_claim(), _verdict(), [])
    second = correct_claim(_dated_claim(), _verdict(), [])
    assert first.corrected_text == second.corrected_text


def test_no_substitution_when_the_value_is_absent_from_the_claim_text() -> None:
    claim = _claim(
        "The tower opened long ago.",
        temporal=[TemporalRef(surface="1950", iso="1950", char_start=0, char_end=4)],
    )
    correction = correct_claim(claim, _verdict(), [])
    assert correction.abstained is True
