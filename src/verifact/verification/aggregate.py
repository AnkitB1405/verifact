"""Stage S5: aggregation and the six-status decision rule.

Owner: P4 (FR-29, FR-30, FR-31). The formula and the rule are documented in
docs/architecture/system-architecture.md §6 and the statuses in
docs/requirements/verification-statuses.md; this module is their implementation
and the two must not diverge.

    E = sum(w_i * p_entail_i) / sum(w_i)       weighted entailment
    C = sum(w_i * p_contra_i) / sum(w_i)       weighted contradiction
    coverage = sum(w_i) / k                    evidence coverage

Three invariants hold regardless of configuration, and each has a test:

1. **No evidence gives UNVERIFIABLE, never CONTRADICTED** (FR-30). Absence of
   evidence is not evidence of falsehood. This is the single rule the whole
   project is organised around.
2. **A MISSING knowledge-graph result never contributes to CONTRADICTED**
   (FR-24). The graph not holding a fact is silence, not denial.
3. **Every component score survives into the verdict** (FR-31). The aggregate
   never replaces its inputs, so H1a and H1b remain analysable after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from verifact.config import VerificationSettings, get_settings
from verifact.contracts import (
    Claim,
    ComponentScores,
    KGCheck,
    KGStatus,
    Verdict,
    VerdictStatus,
)
from verifact.logging import get_logger
from verifact.verification.nli import NliResult
from verifact.verification.weighting import WeightedPassage, cross_source_agreement

_log = get_logger(__name__)


@dataclass(frozen=True)
class Aggregated:
    """Intermediate aggregation result, before calibration."""

    entail: float
    contra: float
    coverage: float
    agreement: float
    status: VerdictStatus
    #: Which signal decided the status, named in the explanation (FR-36).
    deciding_component: str
    rationale: str
    #: How decisive the *deciding* signal was, in [0, 1].
    #:
    #: Set by the branch that made the decision rather than computed once from
    #: |E - C|. A graph-decided verdict whose confidence described the text
    #: margin was incoherent: the explanation named kg_consistency while the
    #: number described a signal that had not decided anything. Each branch
    #: documents its own measure.
    confidence: float = 0.0


def _weighted_mean(weights: list[float], values: list[float]) -> float:
    total = sum(weights)
    if total <= 0.0:
        return 0.0
    return sum(w * v for w, v in zip(weights, values, strict=True)) / total


def _is_outdated(
    weighted: list[WeightedPassage],
    nli: list[NliResult],
    registry_tier: dict[str, int],
) -> bool:
    """True when support is older than an at-least-as-reliable contradiction.

    Both sides must carry publication dates. An undated contradicting passage
    cannot establish that support is *stale*; it produces AMBIGUOUS or
    CONTRADICTED on the ordinary rule instead.
    """
    supporting = [
        (wp, r)
        for wp, r in zip(weighted, nli, strict=True)
        if r.entail >= 0.5 and wp.passage.published_at is not None
    ]
    contradicting = [
        (wp, r)
        for wp, r in zip(weighted, nli, strict=True)
        if r.contra >= 0.5 and wp.passage.published_at is not None
    ]
    if not supporting or not contradicting:
        return False

    support_dates = [wp.passage.published_at for wp, _ in supporting if wp.passage.published_at]
    if not support_dates:
        return False
    newest_support: date = max(support_dates)
    for wp, _ in contradicting:
        published = wp.passage.published_at
        if published is None:
            continue
        contra_tier = registry_tier.get(wp.passage.source_id, 5)
        support_tiers = [registry_tier.get(s.passage.source_id, 5) for s, _ in supporting]
        # Lower tier number is more reliable.
        if published > newest_support and contra_tier <= min(support_tiers):
            return True
    return False


def aggregate(
    claim: Claim,
    weighted: list[WeightedPassage],
    nli: list[NliResult],
    kg_check: KGCheck | None,
    k_requested: int,
    registry_tier: dict[str, int],
    settings: VerificationSettings | None = None,
    similarity_max: float = 1.0,
    kg_source_reliability: float = 0.9,
) -> Aggregated:
    """Combine every signal into one of the six statuses.

    `similarity_max` is load-bearing, not decorative. Retrieval always returns
    *something*, and `relevance` is min-max scaled within a claim's candidate
    set, so the best candidate scores 1.0 even when it is unrelated to the claim
    (EA-07). Coverage alone therefore cannot tell "nothing relevant exists" from
    "the evidence is weak". Absolute similarity can, which is the job stage S1
    was always described as doing.
    """
    cfg = settings or get_settings().verification
    weights = [wp.weight for wp in weighted]
    entail_probs = [r.entail for r in nli]
    contra_probs = [r.contra for r in nli]

    entail = _weighted_mean(weights, entail_probs)
    contra = _weighted_mean(weights, contra_probs)
    coverage = (sum(weights) / k_requested) if k_requested > 0 else 0.0
    agreement = cross_source_agreement(weighted, entail_probs)

    kg_status = kg_check.status if kg_check else KGStatus.NOT_APPLICABLE
    # Reliability of the knowledge base itself. Any verdict the graph decides
    # takes its confidence from this rather than from the text margin.
    kg_reliability = kg_source_reliability

    # 1. Nothing usable came back. The claim may be perfectly true.
    if not weighted or coverage < cfg.tau_cov:
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.UNVERIFIABLE,
            "evidence_coverage",
            f"no usable evidence was retrieved (coverage {coverage:.3f} < {cfg.tau_cov}); "
            "this is a statement about retrieval, not about the claim",
            # Confidence that nothing covers the claim, not that it is false.
            confidence=round(1.0 - min(coverage, 1.0), 6),
        )

    # 1b. Evidence came back but none of it is about this claim. Distinct from
    #     INSUFFICIENT_EVIDENCE, which means on-topic evidence that settles
    #     nothing. Without this branch a private fact nobody has published
    #     ("my neighbour's cat is called Mitzi") gets graded on whatever the
    #     retriever happened to return.
    if similarity_max < cfg.tau_sim:
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.UNVERIFIABLE,
            "similarity",
            f"no retrieved passage is on topic (best similarity {similarity_max:.3f} "
            f"< {cfg.tau_sim}); no trusted source appears to cover this claim",
            # The further below the on-topic threshold, the surer we are that
            # no trusted source covers this claim.
            confidence=round(1.0 - min(similarity_max / max(cfg.tau_sim, 1e-9), 1.0), 6),
        )

    # 2. The knowledge graph actively holds a conflicting value. Only
    #    CONTRADICTED is honoured here - MISSING is silence and is ignored.
    if kg_status is KGStatus.CONTRADICTED:
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.CONTRADICTED,
            "kg_consistency",
            f"the knowledge graph holds a conflicting value: {kg_check.notes if kg_check else ''}",
            # A graph statement is categorical, so the uncertainty lives in
            # the source, not in a margin. The text did not decide this.
            confidence=kg_reliability,
        )

    # 2b. The graph actively confirms the claim. A tier-1 structured source
    #     holding the asserted relation must not be overridden by text NLI,
    #     which is unreliable on off-topic passages (EA-05). Disagreement
    #     between the two signals is AMBIGUOUS, not CONTRADICTED: asserting
    #     contradiction while our most reliable source confirms the claim would
    #     be a false positive of exactly the kind this project exists to avoid.
    if kg_status is KGStatus.SUPPORTED:
        if contra - entail > cfg.tau_con:
            return Aggregated(
                entail,
                contra,
                coverage,
                agreement,
                VerdictStatus.AMBIGUOUS,
                "kg_vs_nli_disagreement",
                f"the knowledge graph confirms this relation but the retrieved text "
                f"contradicts it (C={contra:.3f} vs E={entail:.3f}); the two evidence "
                "types disagree, so no single verdict is given",
                # Confident that the two evidence types disagree, which is
                # exactly what AMBIGUOUS asserts here.
                confidence=round(min(contra, kg_reliability), 6),
            )
        if max(entail, contra) < cfg.tau_weak:
            return Aggregated(
                entail,
                contra,
                coverage,
                agreement,
                VerdictStatus.SUPPORTED,
                "kg_consistency",
                "the knowledge graph confirms this relation and the retrieved text "
                f"does not dispute it (E={entail:.3f}, C={contra:.3f})",
                confidence=kg_reliability,
            )

    # 3. Evidence exists but settles nothing either way.
    if max(entail, contra) < cfg.tau_weak:
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.INSUFFICIENT_EVIDENCE,
            "nli",
            f"evidence was retrieved but neither entails nor contradicts the claim "
            f"(E={entail:.3f}, C={contra:.3f}, both below {cfg.tau_weak})",
            # Sure it settles nothing, in proportion to how weak both sides are.
            confidence=round(1.0 - max(entail, contra) / max(cfg.tau_weak, 1e-9), 6),
        )

    # 4. Sources of comparable standing disagree.
    if entail >= cfg.tau_weak and contra >= cfg.tau_weak:
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.AMBIGUOUS,
            "source_disagreement",
            f"trusted sources disagree (E={entail:.3f}, C={contra:.3f}); "
            "the claim cannot be given one verdict as written",
            # Both sides strong at once is maximal disagreement.
            confidence=round(min(entail, contra), 6),
        )

    # 5. Supported - unless the support is stale and something newer disagrees.
    if entail - contra > cfg.tau_sup:
        if _is_outdated(weighted, nli, registry_tier):
            return Aggregated(
                entail,
                contra,
                coverage,
                agreement,
                VerdictStatus.OUTDATED,
                "recency",
                "the claim is supported only by evidence older than a newer, "
                "at-least-equally-reliable source that disagrees",
                confidence=round(min(abs(entail - contra), 1.0), 6),
            )
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.SUPPORTED,
            "nli",
            f"trusted evidence entails the claim (E={entail:.3f} vs C={contra:.3f})",
            confidence=round(min(abs(entail - contra), 1.0), 6),
        )

    # 6. Contradicted by the text evidence.
    if contra - entail > cfg.tau_con:
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.CONTRADICTED,
            "nli",
            f"trusted evidence contradicts the claim (C={contra:.3f} vs E={entail:.3f})",
            confidence=round(min(abs(entail - contra), 1.0), 6),
        )

    # 7. A claim that is not interpretable standalone cannot be given a verdict.
    if not claim.standalone_interpretable:
        return Aggregated(
            entail,
            contra,
            coverage,
            agreement,
            VerdictStatus.AMBIGUOUS,
            "interpretability",
            "the claim contains an unresolved reference, so it cannot be verified as written",
            # Not a statistical judgement: the referent is either resolved or
            # it is not, and the extractor already established that it is not.
            confidence=1.0,
        )

    return Aggregated(
        entail,
        contra,
        coverage,
        agreement,
        VerdictStatus.INSUFFICIENT_EVIDENCE,
        "nli",
        f"the evidence leans neither way decisively (E={entail:.3f}, C={contra:.3f}; "
        f"margin below {cfg.tau_sup}/{cfg.tau_con})",
        confidence=round(1.0 - min(abs(entail - contra) / max(cfg.tau_sup, 1e-9), 1.0), 6),
    )


def build_verdict(
    claim: Claim,
    result: Aggregated,
    weighted: list[WeightedPassage],
    nli: list[NliResult],
    kg_check: KGCheck | None,
    similarity_max: float,
    similarity_mean: float,
    budget_spent: int,
) -> Verdict:
    """Assemble the `Verdict`, retaining every component score (FR-31).

    `calibrated` is deliberately left False here. Only
    `verification.calibrate` may set it True, and only when a fitted calibrator
    actually loaded (ADR-005) - so no stage can claim a calibration it does not
    have.
    """
    kg_numeric = {
        KGStatus.SUPPORTED: 1.0,
        KGStatus.CONTRADICTED: -1.0,
        KGStatus.MISSING: 0.0,
        KGStatus.NOT_APPLICABLE: 0.0,
    }[kg_check.status if kg_check else KGStatus.NOT_APPLICABLE]

    mean_reliability = sum(wp.reliability for wp in weighted) / len(weighted) if weighted else 0.0
    mean_recency = sum(wp.recency for wp in weighted) / len(weighted) if weighted else 0.0

    scores = ComponentScores(
        similarity_max=round(similarity_max, 6),
        similarity_mean=round(similarity_mean, 6),
        nli_entail=round(max((r.entail for r in nli), default=0.0), 6),
        nli_contra=round(max((r.contra for r in nli), default=0.0), 6),
        nli_neutral=round(max((r.neutral for r in nli), default=0.0), 6),
        source_reliability=round(mean_reliability, 6),
        recency=round(mean_recency, 6),
        cross_source_agreement=round(result.agreement, 6),
        kg_consistency=kg_numeric,
        evidence_coverage=round(min(result.coverage, 1.0), 6),
        weighted_entail=round(result.entail, 6),
        weighted_contra=round(result.contra, 6),
    )

    for_ids = [wp.passage.id for wp, r in zip(weighted, nli, strict=True) if r.entail >= 0.5]
    against_ids = [wp.passage.id for wp, r in zip(weighted, nli, strict=True) if r.contra >= 0.5]

    return Verdict(
        claim_id=claim.id,
        status=result.status,
        confidence=round(min(max(result.confidence, 0.0), 1.0), 6),
        calibrated=False,
        component_scores=scores,
        kg_check=kg_check,
        evidence_for=for_ids,
        evidence_against=against_ids,
        explanation=result.rationale,
        budget_spent=budget_spent,
    )
