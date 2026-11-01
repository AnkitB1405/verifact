"""Stage S1: semantic similarity between a claim and each evidence passage.

Owner: P4 (FR-26).

What this stage is for, and what it is emphatically not for. Cosine similarity
over sentence embeddings measures *topical relatedness* (`reimers2019sbert`). It
cannot tell a statement from its own negation: "Einstein was born in Ulm" and
"Einstein was not born in Ulm" sit almost on top of each other in embedding
space, and `tests/unit/retrieval/test_rankers.py` measures exactly that.

So S1 answers one question only: *is this passage even about the claim?* It
gates whether evidence counts toward coverage. Deciding support or
contradiction is stage S2's job, and no part of the status rule reads a
similarity score directly.
"""

from __future__ import annotations

from verifact.config import RetrievalSettings, get_settings
from verifact.contracts import EvidencePassage
from verifact.logging import get_logger
from verifact.retrieval.rankers import load_embedder, tokenize

_log = get_logger(__name__)


def _jaccard(a: str, b: str) -> float:
    """Token-overlap similarity, used when no embedder is installed.

    Weaker than embeddings and openly so: it scores a paraphrase with no shared
    vocabulary at zero. The run records which backend produced the numbers.
    """
    left, right = set(tokenize(a)), set(tokenize(b))
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def similarity_scores(
    claim_text: str,
    passages: list[EvidencePassage],
    settings: RetrievalSettings | None = None,
) -> list[float]:
    """Similarity of the claim to each passage, in [0, 1]."""
    if not passages:
        return []
    cfg = settings or get_settings().retrieval
    texts = [p.text for p in passages]

    embedder = None if cfg.backend == "lexical" else load_embedder(cfg.embedding_model)
    if embedder is None:
        return [_jaccard(claim_text, t) for t in texts]

    vectors = embedder.encode(
        [claim_text, *texts], normalize_embeddings=True, show_progress_bar=False
    )
    claim_vec, passage_vecs = vectors[0], vectors[1:]
    # Cosine of normalised vectors is in [-1, 1]; clamp to [0, 1] because a
    # negative similarity carries no meaning for our weighting and the
    # ComponentScores contract requires a probability-shaped value.
    return [max(0.0, min(1.0, float(claim_vec @ v))) for v in passage_vecs]


def summarise(scores: list[float]) -> tuple[float, float]:
    """`(max, mean)` similarity, both reported in ComponentScores.

    Both are kept because they say different things: the max says whether *any*
    passage is on topic, the mean says whether the evidence set as a whole is.
    A high max with a low mean means retrieval found one good passage and
    padding, which is worth seeing rather than averaging away.
    """
    if not scores:
        return 0.0, 0.0
    return max(scores), sum(scores) / len(scores)
