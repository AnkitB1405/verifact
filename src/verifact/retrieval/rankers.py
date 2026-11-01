"""Ranking: BM25, dense embeddings, and reciprocal rank fusion.

Owner: P3.

BM25 and dense retrieval fail in *complementary* ways, which is the whole reason
for running both (`robertson2009bm25`, `reimers2019sbert`):

* BM25 scores exact term overlap. It is the only one of the two that reliably
  finds a rare named entity, a number or a date - tokens an embedding model may
  never have seen. It scores a paraphrase with no shared terms at zero.
* Dense retrieval scores semantic proximity, so it finds the paraphrase. It also
  happily rates "Einstein was born in Ulm" and "Einstein was not born in Ulm" as
  near-identical, which is exactly why similarity can never be the verification
  signal and is only stage S1.

Their scores are not on a comparable scale, so they cannot be added. Reciprocal
rank fusion (`cormack2009rrf`) combines *ranks*, needs no normalisation and no
training data, and is three lines. A learned reranker would likely beat it - we
have no training data and no budget, which is the honest answer to that question.
"""

from __future__ import annotations

import re
from typing import Any

from verifact.config import RetrievalSettings, get_settings
from verifact.logging import get_logger

_log = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens, keeping dotted forms.

    Deliberately no stemming. Stemming would collapse "1990" and "1990s" and
    merge "found"/"founded", and for factual claims the exact surface form of a
    number or a date is the thing being checked.
    """
    return _TOKEN_RE.findall(text.lower())


def bm25_scores(
    query: str, docs: list[str], settings: RetrievalSettings | None = None
) -> list[float]:
    """BM25 relevance of each doc to the query. Empty input gives zeros."""
    cfg = settings or get_settings().retrieval
    if not docs:
        return []
    corpus = [tokenize(d) for d in docs]
    if not any(corpus):
        return [0.0] * len(docs)
    from rank_bm25 import BM25Okapi

    model = BM25Okapi(corpus, k1=cfg.bm25_k1, b=cfg.bm25_b)
    return [float(s) for s in model.get_scores(tokenize(query))]


_EMBEDDER: Any | None = None
_EMBEDDER_NAME: str | None = None


def load_embedder(model_name: str) -> Any | None:
    """Load and cache the sentence embedder, or None when unavailable.

    Returning None rather than raising is what makes the `lexical` fallback real:
    a missing optional model degrades retrieval to BM25 instead of failing a run.
    Which backend ran is recorded in the run's provenance, so a degraded result
    is visible rather than silent.
    """
    global _EMBEDDER, _EMBEDDER_NAME
    if _EMBEDDER is not None and model_name == _EMBEDDER_NAME:
        return _EMBEDDER
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        _log.info("sentence-transformers not installed, dense retrieval disabled")
        return None
    try:
        _EMBEDDER = SentenceTransformer(model_name)
    except (OSError, ValueError) as exc:
        _log.warning("embedding model unavailable", extra={"model": model_name, "error": str(exc)})
        return None
    _EMBEDDER_NAME = model_name
    return _EMBEDDER


def dense_scores(
    query: str, docs: list[str], settings: RetrievalSettings | None = None
) -> list[float] | None:
    """Cosine similarity of each doc to the query, or None if no embedder."""
    cfg = settings or get_settings().retrieval
    if not docs:
        return []
    if cfg.backend == "lexical":
        return None
    embedder = load_embedder(cfg.embedding_model)
    if embedder is None:
        if cfg.backend == "dense":
            from verifact.errors import ModelUnavailableError

            raise ModelUnavailableError(
                f"dense backend requested but {cfg.embedding_model} is unavailable"
            )
        return None
    vectors = embedder.encode([query, *docs], normalize_embeddings=True, show_progress_bar=False)
    query_vec, doc_vecs = vectors[0], vectors[1:]
    return [float(query_vec @ v) for v in doc_vecs]


def rrf(rankings: list[list[int]], k: int = 60, n_docs: int = 0) -> list[float]:
    """Reciprocal rank fusion over several rankings of the same documents.

    Args:
        rankings: each entry is document indices ordered best-first.
        k: the RRF constant. 60 is the value used by `cormack2009rrf`; it damps
            the influence of the very top ranks so one retriever cannot dominate.
        n_docs: total document count, needed because a ranking may omit docs.

    Returns:
        One score per document index, higher is better.
    """
    scores = [0.0] * n_docs
    for ranking in rankings:
        for rank, doc_idx in enumerate(ranking, start=1):
            if 0 <= doc_idx < n_docs:
                scores[doc_idx] += 1.0 / (k + rank)
    return scores


def rank_order(scores: list[float]) -> list[int]:
    """Document indices ordered best-first, ties broken by index for determinism.

    Determinism matters: NFR-06 requires identical verdicts for identical input,
    and an unstable sort here would reorder evidence between runs.
    """
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))


def minmax(values: list[float]) -> list[float]:
    """Scale to [0, 1] within one claim's candidate set.

    Used only to turn a fused score into the `relevance` weight. It is explicitly
    *not* a probability and is never compared across claims - RRF scores depend
    on candidate-set size, so a cross-claim comparison would be meaningless.
    """
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return [1.0 if hi > 0 else 0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]
