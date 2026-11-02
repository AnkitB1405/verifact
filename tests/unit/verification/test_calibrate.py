"""Calibration tests. Owner: P4 (FR-32), ADR-005."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from verifact.contracts import Verdict, VerdictStatus
from verifact.verification.calibrate import (
    Calibrator,
    calibrate_verdict,
    expected_calibration_error,
    fit_temperature,
)


def _verdict(status: VerdictStatus = VerdictStatus.SUPPORTED, confidence: float = 0.9) -> Verdict:
    return Verdict(claim_id="c1", status=status, confidence=confidence)


def test_ece_is_zero_for_a_perfectly_calibrated_scorer() -> None:
    confidences = [1.0] * 10
    assert expected_calibration_error(confidences, [True] * 10) == pytest.approx(0.0)


def test_ece_is_large_for_a_confidently_wrong_scorer() -> None:
    assert expected_calibration_error([0.95] * 10, [False] * 10) == pytest.approx(0.95, abs=0.01)


def test_ece_on_empty_input_is_zero_not_an_error() -> None:
    """A metrics table must be able to show an empty slice as empty."""
    assert expected_calibration_error([], []) == 0.0


def test_ece_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        expected_calibration_error([0.5], [True, False])


def test_fitting_reduces_ece_on_an_overconfident_scorer() -> None:
    """The point of the stage: raw margins are not probabilities.

    An uncalibrated scorer emitting 0.75-1.0 while being right 70% of the time
    is exactly the situation guo2017calibration describes.
    """
    rng = random.Random(7)
    raw = [round(rng.uniform(0.75, 1.0), 3) for _ in range(300)]
    correct = [rng.random() < 0.70 for _ in raw]
    before = expected_calibration_error(raw, correct)
    calibrator = fit_temperature(raw, correct, config_hash="test")
    after = expected_calibration_error([calibrator.apply(c) for c in raw], correct)
    assert after < before, f"ECE got worse: {before:.4f} -> {after:.4f}"


def test_fitting_on_empty_data_yields_a_no_op_calibrator() -> None:
    calibrator = fit_temperature([], [])
    assert calibrator.method == "none"
    assert calibrator.apply(0.42) == 0.42


def test_verdict_without_a_calibrator_stays_uncalibrated() -> None:
    """ADR-005: no calibrator means the flag stays False and the score is raw."""
    verdict = calibrate_verdict(_verdict(confidence=0.42), None)
    assert verdict.calibrated is False
    assert verdict.confidence == pytest.approx(0.42)


def test_calibrated_flag_is_only_set_by_this_stage() -> None:
    calibrated = calibrate_verdict(_verdict(), Calibrator("temperature", 1.0))
    assert calibrated.calibrated is True


def test_non_assertive_statuses_are_left_uncalibrated() -> None:
    """The confidence on UNVERIFIABLE describes retrieval, not the claim.

    Calibrating it would imply a claim-level probability it does not have.
    """
    for status in (
        VerdictStatus.UNVERIFIABLE,
        VerdictStatus.INSUFFICIENT_EVIDENCE,
        VerdictStatus.AMBIGUOUS,
    ):
        verdict = calibrate_verdict(_verdict(status=status), Calibrator("temperature", 2.0))
        assert verdict.calibrated is False, status


def test_calibrated_confidence_stays_in_range() -> None:
    for temperature in (0.05, 1.0, 4.0):
        verdict = calibrate_verdict(
            _verdict(confidence=1.0), Calibrator("temperature", temperature)
        )
        assert 0.0 <= verdict.confidence <= 1.0


def test_calibrator_round_trips_through_disk(tmp_path: Path) -> None:
    path = tmp_path / "calibrator.json"
    original = Calibrator("temperature", 1.75, "abc123", 120)
    original.save(path)
    loaded = Calibrator.load(path)
    assert loaded == original


def test_missing_calibrator_file_loads_as_none(tmp_path: Path) -> None:
    assert Calibrator.load(tmp_path / "absent.json") is None


def test_corrupt_calibrator_file_loads_as_none_not_a_crash(tmp_path: Path) -> None:
    path = tmp_path / "calibrator.json"
    path.write_text("{not json")
    assert Calibrator.load(path) is None


def test_calibrator_records_the_pipeline_it_was_fitted_against() -> None:
    """A calibrator fitted against a different pipeline must be detectable."""
    calibrator = fit_temperature([0.8, 0.9], [True, True], config_hash="hash-of-run")
    assert calibrator.config_hash == "hash-of-run"
    assert calibrator.n_fit == 2
