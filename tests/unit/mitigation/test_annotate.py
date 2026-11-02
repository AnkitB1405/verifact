"""Annotated-output tests. Owner: P2 (FR-42)."""

from __future__ import annotations

from verifact.contracts import Verdict, VerdictStatus
from verifact.extraction import extract_claims
from verifact.input import build_document
from verifact.mitigation import annotate, summarise
from verifact.mitigation.annotate import MARKERS

TEXT = "The Eiffel Tower is located in Berlin. The Eiffel Tower is located in Paris."


def _setup(statuses: list[VerdictStatus]):  # type: ignore[no-untyped-def]
    doc = build_document(TEXT)
    claims = [c for c in extract_claims(doc) if c.checkworthy]
    verdicts = [
        Verdict(claim_id=c.id, status=s, confidence=0.9)
        for c, s in zip(claims, statuses, strict=False)
    ]
    return doc, claims, verdicts


def test_flagged_spans_are_marked() -> None:
    doc, claims, verdicts = _setup([VerdictStatus.CONTRADICTED, VerdictStatus.SUPPORTED])
    out = annotate(doc, claims, verdicts)
    assert MARKERS[VerdictStatus.CONTRADICTED] in out
    assert "Berlin" in out


def test_supported_claims_are_not_marked_by_default() -> None:
    """Marking everything is the same as marking nothing."""
    doc, claims, verdicts = _setup([VerdictStatus.SUPPORTED, VerdictStatus.SUPPORTED])
    assert annotate(doc, claims, verdicts) == doc.normalized_text


def test_original_text_is_preserved_around_the_markers() -> None:
    """FR-42: the spans must align, or the wrong words get underlined."""
    doc, claims, verdicts = _setup([VerdictStatus.CONTRADICTED, VerdictStatus.UNVERIFIABLE])
    out = annotate(doc, claims, verdicts)
    stripped = out
    for marker in MARKERS.values():
        stripped = stripped.replace(f"[{marker} ", "")
    stripped = stripped.replace("]", "")
    assert stripped == doc.normalized_text


def test_markers_are_applied_right_to_left_without_shifting_offsets() -> None:
    doc, claims, verdicts = _setup([VerdictStatus.CONTRADICTED, VerdictStatus.CONTRADICTED])
    out = annotate(doc, claims, verdicts)
    assert out.count(MARKERS[VerdictStatus.CONTRADICTED]) == 2
    assert out.index("Berlin") < out.index("Paris")


def test_claims_without_verdicts_are_skipped() -> None:
    doc, claims, _ = _setup([])
    assert annotate(doc, claims, []) == doc.normalized_text


def test_every_status_has_a_marker() -> None:
    assert set(MARKERS) == set(VerdictStatus)


def test_summary_counts_every_status() -> None:
    _, _, verdicts = _setup([VerdictStatus.CONTRADICTED, VerdictStatus.SUPPORTED])
    counts = summarise(verdicts)
    assert set(counts) == {s.value for s in VerdictStatus}
    assert counts["CONTRADICTED"] == 1
    assert counts["SUPPORTED"] == 1
    assert sum(counts.values()) == 2
