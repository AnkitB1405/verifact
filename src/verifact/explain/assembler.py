"""Explanation assembly.

Owner: P4 (FR-35, FR-36). Every verification decision must be traceable, and the
explanation must **name the component that decided it** - not narrate generally
about evidence.

Explanations are assembled deterministically from the component scores. No
language model writes them, for three reasons: the text must be reproducible
(NFR-06), it must not be able to describe a decision the pipeline did not make,
and a generated explanation of a verification system's output would be the one
unverified claim in the whole product.
"""

from __future__ import annotations

from verifact.contracts import (
    Claim,
    EvidencePassage,
    KGStatus,
    Verdict,
    VerdictStatus,
)

#: What each status means, in the user's terms, kept aligned with
#: docs/requirements/verification-statuses.md.
STATUS_MEANING: dict[VerdictStatus, str] = {
    VerdictStatus.SUPPORTED: "trusted sources support this statement",
    VerdictStatus.CONTRADICTED: "trusted sources contradict this statement",
    VerdictStatus.UNVERIFIABLE: (
        "no trusted source covering this statement was found - it may still be true"
    ),
    VerdictStatus.INSUFFICIENT_EVIDENCE: (
        "sources were found but they do not settle this statement either way"
    ),
    VerdictStatus.OUTDATED: "this was supported by older sources, but newer ones disagree",
    VerdictStatus.AMBIGUOUS: "this statement cannot be given a single verdict as written",
}


def confidence_phrase(verdict: Verdict) -> str:
    """Describe the confidence without implying a probability it does not have.

    ADR-005: an uncalibrated score is never presented as a probability, in the
    API, the dashboard or the report. This function is where that wording is
    enforced for every surface at once.
    """
    if verdict.calibrated:
        return f"calibrated confidence {verdict.confidence:.2f}"
    return f"uncalibrated score {verdict.confidence:.2f} (not a probability)"


def explain(
    claim: Claim,
    verdict: Verdict,
    passages: list[EvidencePassage],
) -> str:
    """A human-readable explanation naming the deciding signal."""
    by_id = {p.id: p for p in passages}
    scores = verdict.component_scores
    lines: list[str] = [
        f"{verdict.status.value}: {STATUS_MEANING[verdict.status]}.",
        f"Reason: {verdict.explanation}",
        f"Confidence: {confidence_phrase(verdict)}.",
    ]

    lines.append(
        "Evidence: "
        f"{len(verdict.evidence_for)} supporting, {len(verdict.evidence_against)} contradicting, "
        f"coverage {scores.evidence_coverage:.2f}, "
        f"agreement across sources {scores.cross_source_agreement:.2f}."
    )

    sources = sorted({by_id[pid].source_id for pid in verdict.evidence_for if pid in by_id})
    if sources:
        lines.append(f"Supporting sources: {', '.join(sources)}.")
    against = sorted({by_id[pid].source_id for pid in verdict.evidence_against if pid in by_id})
    if against:
        lines.append(f"Contradicting sources: {', '.join(against)}.")

    if verdict.kg_check and verdict.kg_check.status is not KGStatus.NOT_APPLICABLE:
        kg = verdict.kg_check
        note = f"Knowledge graph: {kg.status.value}"
        if kg.status is KGStatus.MISSING:
            note += " - the graph has no such statement, which is not evidence against the claim"
        if kg.notes:
            note += f". {kg.notes}"
        lines.append(note)
        for path in kg.path_evidence:
            lines.append(f"  graph path: {' | '.join(path)}")

    undated = [pid for pid in verdict.evidence_for if pid in by_id and not by_id[pid].published_at]
    if undated:
        lines.append(
            f"Note: {len(undated)} supporting passage(s) carry no publication date, so they "
            "were not age-discounted."
        )

    if not claim.standalone_interpretable:
        lines.append(
            "Note: this claim contains an unresolved reference, so it was not "
            "interpreted beyond what the sentence itself states."
        )

    if verdict.error:
        lines.append(f"Error during verification: {verdict.error}")

    return "\n".join(lines)


def attach_explanation(claim: Claim, verdict: Verdict, passages: list[EvidencePassage]) -> Verdict:
    """Return the verdict with its full explanation text attached."""
    return verdict.model_copy(update={"explanation": explain(claim, verdict, passages)})
