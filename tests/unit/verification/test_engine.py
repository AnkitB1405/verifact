"""Engine and adaptive-budget tests. Owner: P4 (FR-33)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from verifact.config import Settings
from verifact.contracts import Claim, NumericRef, TemporalRef, VerdictStatus
from verifact.extraction import extract_claims
from verifact.input import build_document
from verifact.verification.aggregate import Aggregated
from verifact.verification.engine import should_escalate, verify_claim

CORPUS = Path("tests/fixtures/local_corpus.jsonl")
ASOF = date(2026, 11, 1)


def _settings(**overrides: object) -> Settings:
    """Offline, lexical-only settings so the engine is testable without network."""
    data: dict[str, object] = {
        "api": {"auth_enabled": False},
        "retrieval": {"backend": "lexical", "offline": True, "top_k": 3, "top_k_escalated": 6},
        "verification": {"backend": "lexical"},
        "kg": {"enabled": False},
    }
    data.update(overrides)
    return Settings(**data)  # type: ignore[arg-type]


def _claim(text: str, **kwargs: object) -> Claim:
    base: dict[str, object] = {
        "sentence_idx": 0,
        "char_start": 0,
        "char_end": len(text),
        "text": text,
    }
    base.update(kwargs)
    return Claim(**base)  # type: ignore[arg-type]


def _result(entail: float, contra: float) -> Aggregated:
    return Aggregated(entail, contra, 0.6, 1.0, VerdictStatus.SUPPORTED, "nli", "test")


# -- escalation policy --------------------------------------------------------


def test_numeric_claim_is_escalated() -> None:
    """Small NLI models are least reliable on numbers; spend more there."""
    claim = _claim(
        "The tower is 330 metres tall.",
        numerics=[NumericRef(surface="330 metres", value=330.0, char_start=13, char_end=23)],
    )
    escalate, reason = should_escalate(claim, _result(0.95, 0.0), _settings())
    assert escalate
    assert "numeric" in reason


def test_temporal_claim_is_escalated() -> None:
    claim = _claim(
        "The tower opened in 1889.",
        temporal=[TemporalRef(surface="1889", iso="1889", char_start=20, char_end=24)],
    )
    escalate, _ = should_escalate(claim, _result(0.95, 0.0), _settings())
    assert escalate


def test_borderline_margin_is_escalated() -> None:
    """A little more evidence could change the answer, so it is worth buying."""
    cfg = _settings()
    margin = cfg.verification.tau_sup
    escalate, reason = should_escalate(_claim("A plain claim."), _result(margin, 0.0), cfg)
    assert escalate
    assert "tau_sup" in reason


def test_decisive_claim_without_numbers_is_not_escalated() -> None:
    escalate, reason = should_escalate(_claim("A plain claim."), _result(0.99, 0.0), _settings())
    assert not escalate
    assert "decisive" in reason


def test_disagreement_is_escalated() -> None:
    cfg = _settings()
    weak = cfg.verification.tau_weak
    escalate, reason = should_escalate(
        _claim("A plain claim."), _result(weak + 0.3, weak + 0.3), cfg
    )
    assert escalate
    assert "disagree" in reason


def test_escalation_can_be_switched_off() -> None:
    """The fixed-budget arm of the H2 experiment must be available."""
    cfg = _settings(verification={"backend": "lexical", "adaptive_budget": False})
    escalate, reason = should_escalate(
        _claim("The tower is 330 metres tall."), _result(0.5, 0.4), cfg
    )
    assert not escalate
    assert "disabled" in reason


# -- end to end, offline ------------------------------------------------------


@pytest.fixture
def offline_claim() -> Claim:
    doc = build_document("The Eiffel Tower is 330 metres tall.", asof=ASOF)
    return [c for c in extract_claims(doc) if c.checkworthy][0]


def test_verify_claim_runs_offline_against_a_local_corpus(offline_claim: Claim) -> None:
    """NFR-05: the whole pipeline must work with no outbound network."""
    verdict = verify_claim(offline_claim, asof=ASOF, settings=_settings(), corpus_path=CORPUS)
    assert verdict.claim_id == offline_claim.id
    assert verdict.status in set(VerdictStatus)
    assert verdict.error is None


def test_verdict_records_budget_spent(offline_claim: Claim) -> None:
    """FR-33: without this the H2 cost/accuracy curve cannot be computed."""
    verdict = verify_claim(offline_claim, asof=ASOF, settings=_settings(), corpus_path=CORPUS)
    assert verdict.budget_spent > 0


def test_escalation_spends_more_budget(offline_claim: Claim) -> None:
    fixed = _settings(verification={"backend": "lexical", "adaptive_budget": False})
    adaptive = _settings()
    cheap = verify_claim(offline_claim, asof=ASOF, settings=fixed, corpus_path=CORPUS)
    spendy = verify_claim(offline_claim, asof=ASOF, settings=adaptive, corpus_path=CORPUS)
    assert spendy.budget_spent > cheap.budget_spent


def test_verdict_is_uncalibrated_without_a_calibrator(offline_claim: Claim) -> None:
    verdict = verify_claim(offline_claim, asof=ASOF, settings=_settings(), corpus_path=CORPUS)
    assert verdict.calibrated is False


def test_claim_with_no_evidence_is_unverifiable_not_contradicted() -> None:
    """FR-30 at the engine level, not just in the aggregation unit."""
    doc = build_document("Zqxthuloa Brennigan invented the flibbertigibbet in 1623.", asof=ASOF)
    claim = [c for c in extract_claims(doc) if c.checkworthy][0]
    verdict = verify_claim(claim, asof=ASOF, settings=_settings(), corpus_path=CORPUS)
    assert verdict.status is not VerdictStatus.CONTRADICTED


def test_determinism(offline_claim: Claim) -> None:
    """NFR-06: identical input, config and seed give identical verdicts."""
    cfg = _settings()
    first = verify_claim(offline_claim, asof=ASOF, settings=cfg, corpus_path=CORPUS)
    second = verify_claim(offline_claim, asof=ASOF, settings=cfg, corpus_path=CORPUS)
    assert first.status == second.status
    assert first.confidence == pytest.approx(second.confidence)
    assert first.component_scores == second.component_scores
