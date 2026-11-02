"""The verification engine: stages S1-S5 for one claim.

Owner: P4 (FR-26…FR-34). The orchestrator calls `verify_claim`; everything about
how a verdict is reached lives here or in the stage modules.

**Adaptive budget (hypothesis H2).** Pass 1 runs every claim cheaply: `top_k`
passages and the small NLI model. A claim is escalated to `top_k_escalated`
passages and the larger model only when it is worth the spend:

* the margin |E - C| sits near a decision threshold, so a little more evidence
  could change the answer;
* the claim carries a number or a date, which is where the NLI literature and
  our own EA-01 say small models are least reliable;
* sources disagree, so more evidence may break the tie.

`budget_spent` is recorded on every verdict, which is what makes the H2
cost/accuracy curve measurable rather than asserted. If H2 fails, the honest
outcome is to report that the adaptive policy bought nothing.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from verifact.config import Settings, get_settings
from verifact.contracts import Claim, EvidencePassage, KGCheck, Verdict
from verifact.errors import VerifactError
from verifact.kg.consistency import check_claim
from verifact.logging import get_logger
from verifact.retrieval.clients.http import SafeClient
from verifact.retrieval.registry import SourceRegistry, get_registry
from verifact.retrieval.retriever import retrieve_for_claim
from verifact.verification.aggregate import Aggregated, aggregate, build_verdict
from verifact.verification.calibrate import Calibrator, calibrate_verdict
from verifact.verification.nli import NliResult, infer
from verifact.verification.similarity import similarity_scores, summarise
from verifact.verification.weighting import WeightedPassage, weigh

_log = get_logger(__name__)


def should_escalate(claim: Claim, result: Aggregated, settings: Settings) -> tuple[bool, str]:
    """Is this claim worth more compute? Returns `(escalate, reason)`."""
    cfg = settings.verification
    if not cfg.adaptive_budget:
        return False, "adaptive budget disabled"

    margin = abs(result.entail - result.contra)
    for threshold, name in ((cfg.tau_sup, "tau_sup"), (cfg.tau_con, "tau_con")):
        if abs(margin - threshold) <= cfg.escalate_margin:
            return True, f"margin {margin:.3f} is within {cfg.escalate_margin} of {name}"

    if claim.numerics or claim.temporal:
        return True, "claim carries a numeric or temporal reference"

    if result.entail >= cfg.tau_weak and result.contra >= cfg.tau_weak:
        return True, "sources disagree"

    return False, "margin is decisive and the claim has no numeric or temporal reference"


def _run_pass(
    claim: Claim,
    passages: list[EvidencePassage],
    kg_check: KGCheck | None,
    registry: SourceRegistry,
    asof: date,
    settings: Settings,
    nli_model: str,
    k_requested: int,
) -> tuple[Aggregated, list[WeightedPassage], list[NliResult], float, float]:
    """One full pass of stages S1-S5 over a fixed evidence set."""
    texts = [p.text for p in passages]
    sims = similarity_scores(claim.text, passages, settings.retrieval)
    sim_max, sim_mean = summarise(sims)
    nli = infer(texts, claim.text, settings.verification, model_name=nli_model)
    weighted = weigh(passages, registry, asof, settings.verification.dedup_threshold)

    # Weighting may have collapsed duplicates, so the NLI list must be realigned
    # to the surviving passages rather than assumed parallel.
    kept_ids = {wp.passage.id for wp in weighted}
    nli_by_id = {p.id: r for p, r in zip(passages, nli, strict=True)}
    nli_kept = [nli_by_id[wp.passage.id] for wp in weighted if wp.passage.id in kept_ids]

    tiers = {sid: registry.get(sid).reliability_tier for sid in registry.source_ids}
    result = aggregate(
        claim,
        weighted,
        nli_kept,
        kg_check,
        k_requested,
        tiers,
        settings.verification,
        similarity_max=sim_max,
    )
    return result, weighted, nli_kept, sim_max, sim_mean


def verify_claim(
    claim: Claim,
    client: SafeClient | None = None,
    registry: SourceRegistry | None = None,
    asof: date | None = None,
    settings: Settings | None = None,
    calibrator: Calibrator | None = None,
    corpus_path: Path | None = None,
) -> Verdict:
    """Verify one claim end to end.

    Any failure in a single stage produces a verdict carrying an `error` rather
    than raising, so one bad claim cannot void a whole run (FR-30 and the
    failure-isolation table in the architecture doc).
    """
    cfg = settings or get_settings()
    registry = registry or get_registry()
    asof = asof or date.today()
    own_client = client is None
    client = client or SafeClient(cfg.retrieval, registry)

    try:
        k = cfg.retrieval.top_k
        passages = retrieve_for_claim(claim, client, k, corpus_path, cfg.retrieval)
        kg_check = check_claim(claim, client, cfg.kg) if cfg.kg.enabled else None

        result, weighted, nli, sim_max, sim_mean = _run_pass(
            claim, passages, kg_check, registry, asof, cfg, cfg.verification.nli_model, k
        )
        budget = len(passages)

        escalate, reason = should_escalate(claim, result, cfg)
        if escalate:
            k2 = cfg.retrieval.top_k_escalated
            _log.info(
                "escalating claim",
                extra={"claim_id": claim.id, "reason": reason, "top_k": k2},
            )
            passages2 = retrieve_for_claim(claim, client, k2, corpus_path, cfg.retrieval)
            if passages2:
                result, weighted, nli, sim_max, sim_mean = _run_pass(
                    claim,
                    passages2,
                    kg_check,
                    registry,
                    asof,
                    cfg,
                    cfg.verification.nli_model_escalated,
                    k2,
                )
                budget += len(passages2)

        verdict = build_verdict(claim, result, weighted, nli, kg_check, sim_max, sim_mean, budget)
        return calibrate_verdict(verdict, calibrator)

    except VerifactError as exc:
        # A failed claim is reported, not hidden, and the run continues.
        _log.warning(
            "claim verification failed",
            extra={"claim_id": claim.id, "error": str(exc)},
        )
        from verifact.contracts import VerdictStatus

        return Verdict(
            claim_id=claim.id,
            status=VerdictStatus.UNVERIFIABLE,
            confidence=0.0,
            explanation="verification could not be completed for this claim",
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if own_client:
            client.close()
