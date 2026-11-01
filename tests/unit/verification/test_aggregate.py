"""Aggregation and status-rule tests. Owner: P4 (FR-29, FR-30, FR-31).

This is the most important test file in the project. The status rule is where
every signal is turned into a claim about someone's text, and two of these tests
encode rules the whole system is organised around.
"""

from __future__ import annotations

from datetime import date

import pytest

from verifact.config import VerificationSettings
from verifact.contracts import KGStatus, VerdictStatus
from verifact.verification.aggregate import aggregate, build_verdict

from .conftest import TIERS, kg, nli, weighted

CFG = VerificationSettings()


def _agg(claim, wps, results, kg_check=None, k=3, similarity_max=0.9, settings=CFG):  # type: ignore[no-untyped-def]
    return aggregate(claim, wps, results, kg_check, k, TIERS, settings, similarity_max)


# -- the two invariants -------------------------------------------------------


def test_no_evidence_is_unverifiable(claim) -> None:  # type: ignore[no-untyped-def]
    """FR-30. The single rule the whole project is organised around.

    Absence of evidence is not evidence of falsehood. If this test ever fails,
    the system is making claims about the world rather than about its sources.
    """
    result = _agg(claim, [], [])
    assert result.status is VerdictStatus.UNVERIFIABLE
    assert result.status is not VerdictStatus.CONTRADICTED
    assert "retrieval" in result.rationale


def test_missing_kg_result_never_causes_contradiction(claim) -> None:  # type: ignore[no-untyped-def]
    """FR-24. The graph not holding a fact is silence, not denial.

    This is the limitation shiralkar2017streams could not escape: a sparse region
    of the graph gives a low score for a true fact. MISSING must therefore be
    inert in the decision rule.
    """
    wps = [weighted()]
    results = [nli(entail=0.95)]
    with_missing = _agg(claim, wps, results, kg(KGStatus.MISSING))
    without_kg = _agg(claim, wps, results, None)
    assert with_missing.status is VerdictStatus.SUPPORTED
    assert with_missing.status == without_kg.status, "MISSING must not change the outcome"


# -- all six statuses are reachable ------------------------------------------


def test_supported(claim) -> None:  # type: ignore[no-untyped-def]
    result = _agg(claim, [weighted()], [nli(entail=0.95)])
    assert result.status is VerdictStatus.SUPPORTED
    assert result.deciding_component == "nli"


def test_contradicted_by_text(claim) -> None:  # type: ignore[no-untyped-def]
    result = _agg(claim, [weighted()], [nli(contra=0.95)])
    assert result.status is VerdictStatus.CONTRADICTED


def test_contradicted_by_knowledge_graph(claim) -> None:  # type: ignore[no-untyped-def]
    """A graph conflict is decisive even when the text is silent."""
    result = _agg(claim, [weighted()], [nli(neutral=1.0)], kg(KGStatus.CONTRADICTED))
    assert result.status is VerdictStatus.CONTRADICTED
    assert result.deciding_component == "kg_consistency"


def test_unverifiable_from_low_coverage(claim) -> None:  # type: ignore[no-untyped-def]
    result = _agg(claim, [weighted(weight=0.01)], [nli(entail=0.9)], k=10)
    assert result.status is VerdictStatus.UNVERIFIABLE


def test_off_topic_evidence_is_unverifiable(claim) -> None:  # type: ignore[no-untyped-def]
    """Regression for EA-07.

    Relevance is min-max scaled per claim, so the best candidate always scores
    1.0 even when nothing retrieved is about the claim. Coverage therefore
    cannot detect this; absolute similarity must.
    """
    result = _agg(claim, [weighted()], [nli(contra=0.8)], similarity_max=0.1)
    assert result.status is VerdictStatus.UNVERIFIABLE
    assert result.deciding_component == "similarity"


def test_insufficient_evidence(claim) -> None:  # type: ignore[no-untyped-def]
    """On-topic evidence that settles nothing - distinct from UNVERIFIABLE."""
    result = _agg(claim, [weighted()], [nli(entail=0.2, contra=0.1)])
    assert result.status is VerdictStatus.INSUFFICIENT_EVIDENCE


def test_ambiguous_from_source_disagreement(claim) -> None:  # type: ignore[no-untyped-def]
    wps = [weighted(source_id="wikipedia"), weighted(source_id="crossref")]
    results = [nli(entail=0.95), nli(contra=0.95)]
    result = _agg(claim, wps, results)
    assert result.status is VerdictStatus.AMBIGUOUS
    assert result.deciding_component == "source_disagreement"


def test_ambiguous_from_unresolved_reference(claim) -> None:  # type: ignore[no-untyped-def]
    """FR-11 reaching the verdict: a guessed referent is worse than AMBIGUOUS."""
    vague = claim.model_copy(update={"standalone_interpretable": False})
    # One side above tau_weak, the other below, and a margin under tau_sup:
    # the only path that reaches the interpretability branch.
    result = _agg(vague, [weighted()], [nli(entail=0.40, contra=0.25)])
    assert result.status is VerdictStatus.AMBIGUOUS
    assert result.deciding_component == "interpretability"


def test_outdated(claim) -> None:  # type: ignore[no-untyped-def]
    """Support predates an at-least-as-reliable source that disagrees."""
    old_support = weighted(
        weight=0.9, source_id="wikipedia", published=date(2019, 1, 1), text="old supporting text"
    )
    new_contra = weighted(
        weight=0.3, source_id="wikidata", published=date(2025, 1, 1), text="new contradicting text"
    )
    result = _agg(claim, [old_support, new_contra], [nli(entail=0.95), nli(contra=0.6)])
    assert result.status is VerdictStatus.OUTDATED
    assert result.deciding_component == "recency"


def test_every_status_is_reachable() -> None:
    """FR-29: a status that cannot be produced is dead documentation."""
    from verifact.contracts import Claim

    text = "The Eiffel Tower is located in Paris."
    c = Claim(sentence_idx=0, char_start=0, char_end=len(text), text=text)
    produced = {
        _agg(c, [], []).status,
        _agg(c, [weighted()], [nli(entail=0.95)]).status,
        _agg(c, [weighted()], [nli(contra=0.95)]).status,
        _agg(c, [weighted()], [nli(entail=0.2, contra=0.1)]).status,
        _agg(
            c,
            [weighted(source_id="wikipedia"), weighted(source_id="crossref")],
            [nli(entail=0.95), nli(contra=0.95)],
        ).status,
        _agg(
            c,
            [
                weighted(
                    weight=0.9,
                    source_id="wikipedia",
                    published=date(2019, 1, 1),
                    text="old supporting text",
                ),
                weighted(
                    weight=0.3,
                    source_id="wikidata",
                    published=date(2025, 1, 1),
                    text="new contradicting text",
                ),
            ],
            [nli(entail=0.95), nli(contra=0.6)],
        ).status,
    }
    assert produced == set(VerdictStatus), f"unreachable: {set(VerdictStatus) - produced}"


# -- knowledge graph interaction (EA-05 fallout) ------------------------------


def test_kg_support_is_honoured_when_text_is_silent(claim) -> None:  # type: ignore[no-untyped-def]
    """A tier-1 structured confirmation is evidence, not decoration."""
    result = _agg(claim, [weighted()], [nli(entail=0.2, contra=0.1)], kg(KGStatus.SUPPORTED))
    assert result.status is VerdictStatus.SUPPORTED
    assert result.deciding_component == "kg_consistency"


def test_kg_support_versus_text_contradiction_is_ambiguous(claim) -> None:  # type: ignore[no-untyped-def]
    """Regression for the Marie Curie false positive.

    The graph confirmed the 1903 Physics prize while the retrieved text
    contradicted it, and the original rule returned CONTRADICTED. Asserting
    contradiction while our most reliable source confirms the claim is the
    failure this project exists to avoid.
    """
    result = _agg(claim, [weighted()], [nli(contra=0.9)], kg(KGStatus.SUPPORTED))
    assert result.status is VerdictStatus.AMBIGUOUS
    assert result.deciding_component == "kg_vs_nli_disagreement"


# -- component scores ---------------------------------------------------------


def test_component_scores_are_all_retained(claim) -> None:  # type: ignore[no-untyped-def]
    """FR-31: the aggregate never replaces its inputs.

    Without this, H1a and H1b cannot be analysed after the fact and the
    project's contribution is unmeasurable.
    """
    wps = [weighted()]
    results = [nli(entail=0.9)]
    result = _agg(claim, wps, results, kg(KGStatus.SUPPORTED))
    verdict = build_verdict(claim, result, wps, results, kg(KGStatus.SUPPORTED), 0.8, 0.6, 3)
    s = verdict.component_scores
    assert s.similarity_max == pytest.approx(0.8)
    assert s.similarity_mean == pytest.approx(0.6)
    assert s.nli_entail == pytest.approx(0.9)
    assert s.source_reliability > 0
    assert s.kg_consistency == 1.0
    assert s.weighted_entail > 0
    assert s.evidence_coverage > 0


def test_verdict_is_never_born_calibrated(claim) -> None:  # type: ignore[no-untyped-def]
    """ADR-005: only the calibration stage may set `calibrated`."""
    wps = [weighted()]
    results = [nli(entail=0.9)]
    verdict = build_verdict(claim, _agg(claim, wps, results), wps, results, None, 0.8, 0.6, 3)
    assert verdict.calibrated is False


def test_evidence_is_split_for_and_against(claim) -> None:  # type: ignore[no-untyped-def]
    wps = [weighted(text="supporting text here"), weighted(text="contradicting text there")]
    results = [nli(entail=0.9), nli(contra=0.9)]
    verdict = build_verdict(claim, _agg(claim, wps, results), wps, results, None, 0.8, 0.6, 3)
    assert len(verdict.evidence_for) == 1
    assert len(verdict.evidence_against) == 1


def test_zero_total_weight_does_not_divide_by_zero(claim) -> None:  # type: ignore[no-untyped-def]
    result = _agg(claim, [weighted(weight=0.0)], [nli(entail=0.9)])
    assert result.entail == 0.0
    assert result.status is VerdictStatus.UNVERIFIABLE
