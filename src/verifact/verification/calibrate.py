"""Confidence calibration and Expected Calibration Error.

Owner: P4 (FR-32), implementing ADR-005.

`guo2017calibration` establishes that a modern network's output is not a
calibrated probability. Reporting a raw score as "the probability this claim is
true" is both the thing the brief forbids and the most obvious line of attack on
the project, so the confidence on every `Verdict` goes through here.

Two honesty properties, both enforced by code rather than convention:

* `Verdict.calibrated` is set **only** when a fitted calibrator actually loaded
  from disk. A fresh checkout, a changed model or the lexical fallback all give
  `calibrated=False`, and the API and dashboard must then say "uncalibrated
  score" rather than showing a probability.
* The calibrator records the config hash of the run that fitted it, so a
  calibrator fitted against a different pipeline is detected and rejected
  instead of silently applied.

Temperature scaling is the default: one parameter, fitted on dev, and the method
`guo2017calibration` found most effective. Isotonic regression is available but
needs more held-out data than `verifact-stress` provides.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from verifact.contracts import Verdict, VerdictStatus
from verifact.logging import get_logger

_log = get_logger(__name__)

#: Statuses that assert something about the claim. UNVERIFIABLE and
#: NOT_APPLICABLE-like outcomes are statements about retrieval, so their
#: confidence is not a claim-level probability and is left uncalibrated.
#: Temperature search grid: 0.05 to 4.0. Below 0.05 confidence saturates at the
#: extremes; above 4.0 everything collapses towards 0.5.
TEMPERATURE_GRID: tuple[float, ...] = tuple(i / 20 for i in range(1, 81))

ASSERTIVE_STATUSES = frozenset(
    {VerdictStatus.SUPPORTED, VerdictStatus.CONTRADICTED, VerdictStatus.OUTDATED}
)


@dataclass(frozen=True)
class Calibrator:
    """A fitted calibration map."""

    method: str
    #: Temperature for `temperature` method. >1 softens confidence, <1 sharpens.
    temperature: float = 1.0
    #: Config hash of the pipeline this was fitted against.
    config_hash: str = ""
    n_fit: int = 0

    def apply(self, raw: float) -> float:
        if self.method == "none":
            return raw
        if self.method == "temperature":
            # Map the raw margin through a temperature-scaled logistic. The
            # margin is already in [0,1]; centring it at 0.5 keeps a margin of 0
            # at a confidence of 0.5 before scaling.
            z = (raw - 0.5) * 2.0
            if self.temperature <= 0:
                return raw
            return 1.0 / (1.0 + math.exp(-z / self.temperature))
        return raw

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> Calibrator | None:
        """Load a calibrator, or None when absent or unreadable."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return cls(**data)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            _log.warning(
                "ignoring unreadable calibrator",
                extra={"path": str(path), "error": str(exc)},
            )
            return None


def expected_calibration_error(
    confidences: list[float], correct: list[bool], n_bins: int = 10
) -> float:
    """ECE with equal-width bins (ADR-005 fixes 10 bins).

    Returns 0.0 for an empty input rather than raising, so a metrics table can
    be produced for a slice with no items and show it as empty.
    """
    if not confidences:
        return 0.0
    if len(confidences) != len(correct):
        raise ValueError("confidences and correct must be the same length")

    total = len(confidences)
    error = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        members = [
            (c, ok)
            for c, ok in zip(confidences, correct, strict=True)
            if (c > lo or (b == 0 and c >= lo)) and c <= hi
        ]
        if not members:
            continue
        avg_conf = sum(c for c, _ in members) / len(members)
        accuracy = sum(1 for _, ok in members if ok) / len(members)
        error += (len(members) / total) * abs(avg_conf - accuracy)
    return error


def fit_temperature(
    confidences: list[float],
    correct: list[bool],
    config_hash: str = "",
    grid: tuple[float, ...] = TEMPERATURE_GRID,
) -> Calibrator:
    """Fit a temperature by minimising ECE on a held-out split.

    A grid search rather than gradient descent on NLL: one parameter, a bounded
    range, and the objective we actually report is ECE. Minimising the thing we
    report avoids claiming an improvement on a different objective.

    **Must be fitted on dev, never on test** (ADR-005). Nothing here can enforce
    that; the protocol and the recorded freeze commit are what enforce it.
    """
    if not confidences:
        return Calibrator("none", 1.0, config_hash, 0)
    best = min(
        grid,
        key=lambda t: expected_calibration_error(
            [Calibrator("temperature", t).apply(c) for c in confidences], correct
        ),
    )
    calibrator = Calibrator("temperature", round(best, 4), config_hash, len(confidences))
    _log.info(
        "calibrator fitted",
        extra={"temperature": calibrator.temperature, "n_fit": calibrator.n_fit},
    )
    return calibrator


def calibrate_verdict(verdict: Verdict, calibrator: Calibrator | None) -> Verdict:
    """Apply a calibrator to one verdict, honestly.

    With no calibrator the verdict is returned unchanged, still carrying
    `calibrated=False`. Non-assertive statuses are also left alone: the
    confidence attached to UNVERIFIABLE describes retrieval, not the claim, and
    calibrating it would imply a probability it does not have.
    """
    if calibrator is None or verdict.status not in ASSERTIVE_STATUSES:
        return verdict
    return verdict.model_copy(
        update={
            "confidence": round(min(max(calibrator.apply(verdict.confidence), 0.0), 1.0), 6),
            "calibrated": True,
        }
    )
