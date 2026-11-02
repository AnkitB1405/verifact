"""Annotated output: the original text with problem spans marked.

Owner: P2 (FR-42). The annotation is built from `Claim.char_start/char_end`,
which index into `Document.normalized_text` - the invariant the input module
exists to guarantee. If those offsets are wrong, this module silently underlines
the wrong words, which is why the offset test is property-based.

Spans are applied right-to-left so that inserting a marker never shifts the
offsets of a span not yet processed.
"""

from __future__ import annotations

from verifact.contracts import Claim, Document, Verdict, VerdictStatus

#: Short markers for inline annotation. Deliberately plain text: the same
#: annotated string is used in the API payload, the dashboard and an exported
#: report, so it must not carry HTML.
MARKERS: dict[VerdictStatus, str] = {
    VerdictStatus.SUPPORTED: "✓",
    VerdictStatus.CONTRADICTED: "✗",
    VerdictStatus.UNVERIFIABLE: "?",
    VerdictStatus.INSUFFICIENT_EVIDENCE: "~",
    VerdictStatus.OUTDATED: "⌛",
    VerdictStatus.AMBIGUOUS: "±",
}

#: Statuses worth drawing the reader's attention to. SUPPORTED is not marked
#: inline: marking everything is the same as marking nothing.
FLAGGED = frozenset(
    {
        VerdictStatus.CONTRADICTED,
        VerdictStatus.UNVERIFIABLE,
        VerdictStatus.INSUFFICIENT_EVIDENCE,
        VerdictStatus.OUTDATED,
        VerdictStatus.AMBIGUOUS,
    }
)


def annotate(
    document: Document,
    claims: list[Claim],
    verdicts: list[Verdict],
    flagged_only: bool = True,
) -> str:
    """Return the normalised text with inline status markers.

    Overlapping spans are a real possibility: one sentence can yield several
    claims whose source regions overlap (a modifier extracted from inside the
    main clause). Only the first span at a given start position is marked, so the
    output stays readable rather than nesting markers.
    """
    by_claim = {v.claim_id: v for v in verdicts}
    spans: list[tuple[int, int, str]] = []
    for claim in claims:
        verdict = by_claim.get(claim.id)
        if verdict is None:
            continue
        if flagged_only and verdict.status not in FLAGGED:
            continue
        spans.append((claim.char_start, claim.char_end, MARKERS[verdict.status]))

    # Longest span first at a shared start, so the outer region wins.
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    chosen: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, marker in spans:
        if start >= last_end:
            chosen.append((start, end, marker))
            last_end = end

    text = document.normalized_text
    # Right to left: an earlier insertion would shift every later offset.
    for start, end, marker in sorted(chosen, reverse=True):
        text = f"{text[:start]}[{marker} {text[start:end]}]{text[end:]}"
    return text


def summarise(verdicts: list[Verdict]) -> dict[str, int]:
    """Counts per status, for the dashboard header and the exported report."""
    counts = dict.fromkeys((s.value for s in VerdictStatus), 0)
    for verdict in verdicts:
        counts[verdict.status.value] += 1
    return counts
