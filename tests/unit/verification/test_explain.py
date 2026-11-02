"""Explanation tests. Owner: P4 (FR-35, FR-36)."""

from __future__ import annotations

from verifact.contracts import (
    Claim,
    ComponentScores,
    KGCheck,
    KGStatus,
    Verdict,
    VerdictStatus,
)
from verifact.explain import confidence_phrase, explain

from .conftest import passage

TEXT = "The Eiffel Tower is located in Paris."
CLAIM = Claim(sentence_idx=0, char_start=0, char_end=len(TEXT), text=TEXT)


def _verdict(**kwargs: object) -> Verdict:
    base: dict[str, object] = {
        "claim_id": CLAIM.id,
        "status": VerdictStatus.SUPPORTED,
        "confidence": 0.8,
        "explanation": "trusted evidence entails the claim",
        "component_scores": ComponentScores(evidence_coverage=0.6, cross_source_agreement=1.0),
    }
    base.update(kwargs)
    return Verdict(**base)  # type: ignore[arg-type]


def test_explanation_names_the_status_and_its_meaning() -> None:
    text = explain(CLAIM, _verdict(), [])
    assert "SUPPORTED" in text
    assert "trusted sources support" in text


def test_explanation_includes_the_deciding_reason() -> None:
    """FR-36: the explanation must say which signal decided it."""
    text = explain(CLAIM, _verdict(explanation="the knowledge graph holds a conflicting value"), [])
    assert "knowledge graph holds a conflicting value" in text


def test_uncalibrated_confidence_is_never_called_a_probability() -> None:
    """ADR-005, enforced in one place for every surface that shows a number."""
    phrase = confidence_phrase(_verdict(calibrated=False))
    assert "uncalibrated" in phrase
    assert "not a probability" in phrase


def test_calibrated_confidence_is_labelled_as_calibrated() -> None:
    assert "calibrated confidence" in confidence_phrase(_verdict(calibrated=True))


def test_unverifiable_explanation_says_the_claim_may_still_be_true() -> None:
    """The project's central distinction, stated in the words the user reads."""
    text = explain(CLAIM, _verdict(status=VerdictStatus.UNVERIFIABLE, confidence=0.0), [])
    assert "may still be true" in text


def test_missing_kg_result_is_explained_as_not_evidence_against() -> None:
    """FR-24 surfaced to the user, not just enforced internally."""
    verdict = _verdict(
        kg_check=KGCheck(claim_id=CLAIM.id, status=KGStatus.MISSING, notes="no statement")
    )
    text = explain(CLAIM, verdict, [])
    assert "not evidence against" in text


def test_kg_path_is_shown_when_present() -> None:
    """FR-25: the path is the explanation."""
    verdict = _verdict(
        kg_check=KGCheck(
            claim_id=CLAIM.id,
            status=KGStatus.SUPPORTED,
            path_evidence=[["Eiffel Tower --P131--> 7th arrondissement", "7th --P131--> Paris"]],
        )
    )
    text = explain(CLAIM, verdict, [])
    assert "graph path" in text
    assert "7th arrondissement" in text


def test_sources_are_named() -> None:
    supporting = passage(source_id="wikipedia")
    verdict = _verdict(evidence_for=[supporting.id])
    text = explain(CLAIM, verdict, [supporting])
    assert "wikipedia" in text


def test_undated_evidence_is_disclosed() -> None:
    """The user should know a passage was not age-discounted and why."""
    undated = passage(source_id="crossref", published=None)
    verdict = _verdict(evidence_for=[undated.id])
    text = explain(CLAIM, verdict, [undated])
    assert "no publication date" in text


def test_unresolved_reference_is_disclosed() -> None:
    vague = CLAIM.model_copy(update={"standalone_interpretable": False})
    text = explain(vague, _verdict(status=VerdictStatus.AMBIGUOUS), [])
    assert "unresolved reference" in text


def test_claim_level_error_is_surfaced_not_swallowed() -> None:
    text = explain(CLAIM, _verdict(error="RetrievalError: source unreachable"), [])
    assert "Error during verification" in text
    assert "source unreachable" in text


def test_explanation_is_deterministic() -> None:
    """NFR-06. No model writes these, so identical input gives identical text."""
    verdict = _verdict()
    assert explain(CLAIM, verdict, []) == explain(CLAIM, verdict, [])


def test_every_status_has_a_meaning_defined() -> None:
    from verifact.explain.assembler import STATUS_MEANING

    assert set(STATUS_MEANING) == set(VerdictStatus)
