"""Evidence-grounded correction by substitution.

Owner: P2 (FR-37…FR-41).

**No language model generates a correction.** Corrections are produced by
substituting a value taken from cited evidence into the original claim. That is a
deliberate architectural choice, not a limitation of effort:

* **FR-39 (introduce no unsupported claim) is satisfied by construction.** The
  only thing that changes is one span, and the replacement came from a cited
  passage or a knowledge-graph statement. A generative corrector can only
  *promise* not to add unsupported content; RARR (`gao2023rarr`) uses an LLM
  reviser and the paper's own framing is that it may introduce new content.
* The output is reproducible (NFR-06) and the diff shown to the user is exactly
  what the evidence supports.
* It cannot be prompt-injected, because retrieved text is never an instruction -
  only a source of a value.

The cost is honest and stated: we can correct a wrong number, date or entity, and
we **cannot** rewrite a badly-formed or structurally wrong claim. When
substitution is not possible, the module **abstains** (FR-38) rather than
guessing - and abstention is the common case, which is the correct behaviour for
a system whose errors are expensive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from verifact.config import VerificationSettings, get_settings
from verifact.contracts import (
    Citation,
    Claim,
    Correction,
    EvidencePassage,
    KGStatus,
    Verdict,
    VerdictStatus,
)
from verifact.logging import get_logger

_log = get_logger(__name__)

#: Statuses worth attempting a correction for. SUPPORTED needs none;
#: UNVERIFIABLE and INSUFFICIENT_EVIDENCE have nothing to correct *from*, and
#: inventing a replacement would be the fabrication the project exists to catch.
CORRECTABLE = frozenset({VerdictStatus.CONTRADICTED, VerdictStatus.OUTDATED})

#: A correction is only offered when the evidence behind it is at least this
#: strong. Below it, abstaining is more useful than a low-confidence rewrite.
MIN_EVIDENCE_CONFIDENCE = 0.30

_YEAR_RE = re.compile(r"\b(1\d{3}|20\d{2}|21\d{2})\b")
_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")


@dataclass(frozen=True)
class Substitution:
    """One grounded replacement: what to change, to what, and on whose authority."""

    original: str
    replacement: str
    kind: str
    citation: Citation


def _kg_substitution(claim: Claim, verdict: Verdict) -> Substitution | None:
    """Pull the conflicting value out of the knowledge-graph note.

    The KG stage already reports what the graph holds ("claim says 1950, graph
    holds ['1889']"), so the authoritative value is available without a second
    lookup.
    """
    check = verdict.kg_check
    if check is None or check.status is not KGStatus.CONTRADICTED or not check.notes:
        return None

    match = re.search(r"graph holds \[([^\]]*)\]", check.notes)
    if not match:
        return None
    values = [v.strip().strip("'\"+") for v in match.group(1).split(",") if v.strip()]
    if not values:
        return None
    replacement = values[0]

    # What in the claim does this replace? Prefer an explicit temporal or
    # numeric mention, since those are what the graph compared against.
    if claim.temporal and _YEAR_RE.fullmatch(replacement):
        return Substitution(
            original=claim.temporal[0].surface,
            replacement=replacement,
            kind="temporal",
            citation=Citation(passage_id="kg", source_id="wikidata"),
        )
    if claim.numerics and _NUMBER_RE.fullmatch(replacement):
        numeric = claim.numerics[0]
        unit = f" {numeric.unit}" if numeric.unit else ""
        return Substitution(
            original=numeric.surface,
            replacement=f"{replacement}{unit}",
            kind="numeric",
            citation=Citation(passage_id="kg", source_id="wikidata"),
        )
    return None


def _passage_substitution(
    claim: Claim, verdict: Verdict, passages: list[EvidencePassage]
) -> Substitution | None:
    """Find a replacement value in a cited contradicting passage.

    Only values of the *same kind* as the claim's own mention are considered. A
    year may replace a year and a number a number; nothing else is touched,
    because any broader edit would be the module writing prose.
    """
    by_id = {p.id: p for p in passages}
    contradicting = [by_id[pid] for pid in verdict.evidence_against if pid in by_id]
    if not contradicting:
        return None

    for passage in contradicting:
        citation = Citation(passage_id=passage.id, source_id=passage.source_id, url=passage.url)
        if claim.temporal:
            claimed = claim.temporal[0].surface
            candidates = [y for y in _YEAR_RE.findall(passage.text) if y != claimed]
            if candidates:
                return Substitution(claimed, candidates[0], "temporal", citation)
        if claim.numerics:
            numeric = claim.numerics[0]
            claimed_num = numeric.surface
            candidates = [n for n in _NUMBER_RE.findall(passage.text) if n not in claimed_num]
            if candidates:
                unit = f" {numeric.unit}" if numeric.unit else ""
                return Substitution(claimed_num, f"{candidates[0]}{unit}", "numeric", citation)
    return None


def _abstain(claim: Claim, reason: str, ceiling: float = 0.0) -> Correction:
    _log.info("abstaining from correction", extra={"claim_id": claim.id, "reason": reason})
    return Correction(
        claim_id=claim.id,
        corrected_text=None,
        abstained=True,
        abstain_reason=reason,
        max_supportable_confidence=ceiling,
    )


def correct_claim(
    claim: Claim,
    verdict: Verdict,
    passages: list[EvidencePassage],
    settings: VerificationSettings | None = None,
) -> Correction:
    """Propose an evidence-grounded correction, or abstain.

    The returned `Correction` always satisfies the contract invariants: an
    abstention carries a reason and no text, and a correction carries text and at
    least one citation.
    """
    _ = settings or get_settings().verification

    if verdict.status not in CORRECTABLE:
        return _abstain(
            claim,
            f"status is {verdict.status.value}: there is nothing to correct from "
            "(a correction needs evidence of what the right value is, not just "
            "evidence that the claim is unsupported)",
        )

    ceiling = verdict.confidence
    if ceiling < MIN_EVIDENCE_CONFIDENCE:
        return _abstain(
            claim,
            f"evidence confidence {ceiling:.2f} is below the "
            f"{MIN_EVIDENCE_CONFIDENCE:.2f} threshold required to propose a rewrite",
            ceiling,
        )

    substitution = _kg_substitution(claim, verdict) or _passage_substitution(
        claim, verdict, passages
    )
    if substitution is None:
        return _abstain(
            claim,
            "the evidence shows the claim is wrong but does not supply a "
            "replacement value of the same kind, so no grounded correction is "
            "possible",
            ceiling,
        )

    if substitution.original not in claim.text:
        return _abstain(
            claim,
            "the value to be replaced could not be located in the claim text",
            ceiling,
        )

    corrected = claim.text.replace(substitution.original, substitution.replacement, 1)
    if corrected == claim.text:
        return _abstain(claim, "substitution would not change the claim", ceiling)

    _log.info(
        "correction proposed",
        extra={
            "claim_id": claim.id,
            "kind": substitution.kind,
            "source": substitution.citation.source_id,
        },
    )
    return Correction(
        claim_id=claim.id,
        corrected_text=corrected,
        abstained=False,
        abstain_reason=None,
        citations=[substitution.citation],
        # FR-40: a correction may never be more confident than its evidence.
        max_supportable_confidence=ceiling,
    )
