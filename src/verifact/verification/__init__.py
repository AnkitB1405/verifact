"""Verification engine. Owner: P4. Contract produced: `Verdict`."""

from verifact.verification.aggregate import aggregate, build_verdict
from verifact.verification.calibrate import (
    Calibrator,
    calibrate_verdict,
    expected_calibration_error,
    fit_temperature,
)
from verifact.verification.engine import should_escalate, verify_claim
from verifact.verification.nli import NliResult, infer
from verifact.verification.similarity import similarity_scores, summarise
from verifact.verification.weighting import recency_factor, weigh

__all__ = [
    "Calibrator",
    "NliResult",
    "aggregate",
    "build_verdict",
    "calibrate_verdict",
    "expected_calibration_error",
    "fit_temperature",
    "infer",
    "recency_factor",
    "should_escalate",
    "similarity_scores",
    "summarise",
    "verify_claim",
    "weigh",
]
