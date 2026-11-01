"""Stage S4: evidence weighting by source reliability, recency and relevance.

Owner: P4 (FR-28, FR-34). **This is the stage the project's novelty claim rests
on.** The gap matrix shows no surveyed system weights evidence by source
reliability or age: FEVER, FEVEROUS and FActScore use Wikipedia alone, and RARR
uses whatever a web search returns. All of them treat their evidence pool as
uniformly trustworthy.

The weight of passage *i* is

    w_i = r(source_i) · rho(age_i) · rel_i

* `r` is the source's base reliability from the registry, in (0, 1].
* `rho` is an exponential recency decay, `0.5 ** (age_days / halflife_days)`,
  with a per-source-kind half-life. A passage with **no publication date** gets
  `rho = 1.0` and is recorded as undated - it is never assumed to be recent, and
  never penalised for a gap in the source's metadata.
* `rel` is the fused retrieval relevance, min-max scaled within this claim's
  candidate set.

Near-duplicate passages are collapsed first (FR-34). Two mirrors of one article
are one piece of evidence, not two independent confirmations - the lesson taken
from `kuhn2023semantic`, where sequence-level counting overstates agreement
because different surface forms carry the same meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from verifact.contracts import EvidencePassage
from verifact.logging import get_logger
from verifact.retrieval.rankers import tokenize
from verifact.retrieval.registry import SourceRegistry

_log = get_logger(__name__)


@dataclass(frozen=True)
class WeightedPassage:
    """A passage with its weight and the three factors that produced it."""

    passage: EvidencePassage
    reliability: float
    recency: float
    relevance: float
    weight: float
    undated: bool
    #: Ids of passages collapsed into this one as near-duplicates.
    duplicates: tuple[str, ...] = ()


def recency_factor(
    published: date | None, halflife_days: int | None, asof: date
) -> tuple[float, bool]:
    """Exponential decay by age. Returns `(factor, undated)`.

    A missing date gives 1.0 rather than a penalty. Penalising it would
    systematically down-weight sources with sparse metadata, which is a property
    of the source's bookkeeping and not of the claim's support.
    """
    if published is None:
        return 1.0, True
    if halflife_days is None or halflife_days <= 0:
        return 1.0, False
    age_days = max((asof - published).days, 0)
    return 0.5 ** (age_days / halflife_days), False


def _near_duplicate(a: str, b: str, threshold: float) -> bool:
    """Jaccard token overlap, used for collapsing mirrored passages.

    Token overlap rather than embeddings: this runs on every passage pair and
    must work on the lexical backend too. It catches the case that actually
    occurs - the same text served from two URLs - and is not trying to detect
    paraphrase.
    """
    left, right = set(tokenize(a)), set(tokenize(b))
    if not left or not right:
        return False
    return len(left & right) / len(left | right) >= threshold


def deduplicate(
    passages: list[EvidencePassage], threshold: float = 0.95
) -> list[tuple[EvidencePassage, tuple[str, ...]]]:
    """Collapse near-identical passages, keeping the first of each group."""
    kept: list[tuple[EvidencePassage, list[str]]] = []
    for passage in passages:
        for original, dupes in kept:
            if _near_duplicate(original.text, passage.text, threshold):
                dupes.append(passage.id)
                break
        else:
            kept.append((passage, []))
    if any(dupes for _, dupes in kept):
        _log.info(
            "collapsed near-duplicate passages",
            extra={"n_collapsed": sum(len(d) for _, d in kept)},
        )
    return [(p, tuple(d)) for p, d in kept]


def weigh(
    passages: list[EvidencePassage],
    registry: SourceRegistry,
    asof: date,
    dedup_threshold: float = 0.95,
) -> list[WeightedPassage]:
    """Weight every passage, after collapsing duplicates."""
    out: list[WeightedPassage] = []
    for passage, duplicates in deduplicate(passages, dedup_threshold):
        source = registry.get(passage.source_id)
        recency, undated = recency_factor(passage.published_at, source.halflife_days, asof)
        relevance = passage.scores.relevance
        out.append(
            WeightedPassage(
                passage=passage,
                reliability=source.base_reliability,
                recency=round(recency, 6),
                relevance=relevance,
                weight=round(source.base_reliability * recency * relevance, 6),
                undated=undated,
                duplicates=duplicates,
            )
        )
    return out


def cross_source_agreement(weighted: list[WeightedPassage], entail: list[float]) -> float:
    """How much *distinct sources* agree that the claim is entailed.

    Counted per source rather than per passage, so six paragraphs from one
    article cannot look like six independent confirmations. Returns the share of
    represented sources whose best passage entails the claim.
    """
    if not weighted:
        return 0.0
    best_by_source: dict[str, float] = {}
    for wp, e in zip(weighted, entail, strict=True):
        sid = wp.passage.source_id
        best_by_source[sid] = max(best_by_source.get(sid, 0.0), e)
    if not best_by_source:
        return 0.0
    agreeing = sum(1 for v in best_by_source.values() if v >= 0.5)
    return agreeing / len(best_by_source)
