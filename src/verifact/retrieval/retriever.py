"""The retrieval stage: claim in, ranked evidence passages out.

Owner: P3. Contract produced: `list[EvidencePassage]` (FR-15, FR-16).

Shape of the stage:

1. Build a query from the claim. Entity surface forms are repeated so BM25
   weights them, because the entity is what identifies the right document while
   the rest of the claim is what we are checking.
2. Gather *candidates* from every enabled source. No ranking yet - a source that
   returns 6 paragraphs has not told us which matters.
3. Score all candidates together with BM25 and (when available) embeddings,
   fuse the two rankings with RRF, and keep the top k.

Candidates from all sources are pooled and ranked *together* rather than taking
the best few from each. Taking a quota per source would force low-quality
evidence into the set whenever a weak source happened to be enabled, and the
weighting stage would then have to undo it.
"""

from __future__ import annotations

from pathlib import Path

from verifact.config import RetrievalSettings, get_settings
from verifact.contracts import Claim, EvidencePassage, RetrievalScores
from verifact.errors import RetrievalError
from verifact.logging import get_logger
from verifact.retrieval.clients import crossref, local, wikipedia
from verifact.retrieval.clients.http import SafeClient
from verifact.retrieval.rankers import (
    bm25_scores,
    dense_scores,
    minmax,
    rank_order,
    rrf,
)

_log = get_logger(__name__)

#: Sources queried for free-text evidence. Wikidata is handled by the KG stage,
#: not here: its value is structured statements, not prose.
TEXT_SOURCES = ("wikipedia", "crossref", "local_corpus")


def build_query(claim: Claim) -> str:
    """A retrieval query for a claim.

    Entity surfaces are prepended as well as left in place, so a lexical
    retriever weights the identifying entity above the predicate. Without this,
    "The Eiffel Tower is 330 metres tall" retrieves documents about height in
    general as readily as documents about the tower.
    """
    entities = " ".join(e.surface for e in claim.entities)
    return f"{entities} {claim.text}".strip() if entities else claim.text


def gather_candidates(
    claim: Claim,
    client: SafeClient,
    corpus_path: Path | None = None,
    sources: tuple[str, ...] = TEXT_SOURCES,
) -> list[EvidencePassage]:
    """Unranked candidate passages from every enabled source.

    A source that fails is logged and skipped. Failing the whole claim because
    one source timed out would turn a transient outage into a CONTRADICTED or
    UNVERIFIABLE verdict, which is a correctness bug, not a reliability one.
    """
    query = build_query(claim)
    out: list[EvidencePassage] = []

    if "wikipedia" in sources:
        out.extend(wikipedia.retrieve(client, claim.id, query))
    if "crossref" in sources:
        out.extend(crossref.retrieve(client, claim.id, query))
    if "local_corpus" in sources and corpus_path is not None:
        out.extend(local.to_passages(local.load_corpus(corpus_path), claim.id))

    _log.info(
        "candidates gathered",
        extra={"claim_id": claim.id, "n_candidates": len(out), "sources": list(sources)},
    )
    return out


def rank_passages(
    claim: Claim,
    candidates: list[EvidencePassage],
    top_k: int,
    settings: RetrievalSettings | None = None,
) -> list[EvidencePassage]:
    """Score, fuse and truncate. Returns passages carrying their scores."""
    if not candidates:
        return []
    cfg = settings or get_settings().retrieval
    query = build_query(claim)
    texts = [p.text for p in candidates]

    lexical = bm25_scores(query, texts, cfg)
    semantic = dense_scores(query, texts, cfg)

    rankings = [rank_order(lexical)]
    if semantic is not None:
        rankings.append(rank_order(semantic))
    fused = rrf(rankings, k=cfg.rrf_k, n_docs=len(candidates))
    relevance = minmax(fused)

    scored = [
        p.model_copy(
            update={
                "scores": RetrievalScores(
                    bm25=lexical[i],
                    dense=semantic[i] if semantic is not None else None,
                    rrf=fused[i],
                    relevance=relevance[i],
                )
            }
        )
        for i, p in enumerate(candidates)
    ]
    scored.sort(key=lambda p: (-p.scores.rrf, p.id))
    return scored[:top_k]


def retrieve_for_claim(
    claim: Claim,
    client: SafeClient | None = None,
    top_k: int | None = None,
    corpus_path: Path | None = None,
    settings: RetrievalSettings | None = None,
) -> list[EvidencePassage]:
    """Full retrieval for one claim: gather, rank, truncate.

    Returns an empty list when nothing is found. That is a legitimate outcome
    and the aggregation stage turns it into UNVERIFIABLE - never CONTRADICTED
    (FR-30).
    """
    cfg = settings or get_settings().retrieval
    own_client = client is None
    client = client or SafeClient(cfg)
    try:
        candidates = gather_candidates(claim, client, corpus_path)
        return rank_passages(claim, candidates, top_k or cfg.top_k, cfg)
    except RetrievalError as exc:
        _log.warning("retrieval failed for claim", extra={"claim_id": claim.id, "error": str(exc)})
        return []
    finally:
        if own_client:
            client.close()
