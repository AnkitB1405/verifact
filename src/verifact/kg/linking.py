"""Entity linking: surface form to knowledge-base identifier.

Owner: P3 (FR-20, FR-21).

The requirement is that **ambiguity is never resolved by guessing**. "Washington"
is a US state, a city, a surname and a given name; "Eiffel Tower" is a tower and
also two different paintings of it. Picking the most popular sense silently would
make the KG stage check the wrong entity, and the wrong entity yields
CONTRADICTED on a true claim - the worst failure this project can produce.

Surface form alone cannot disambiguate those cases, so this module does not try.
It ranks candidates, flags the mention as ambiguous when more than one candidate
matches the label exactly, and hands the whole candidate list onward. The
consistency stage then disambiguates **by the claim's own relation**: it tries
each candidate and uses the one the relation actually applies to. If the relation
applies to several with conflicting values, it declines. Popularity never decides
anything.

`confidence` is a heuristic ranking score, not a probability, and is labelled as
such everywhere it surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from verifact.contracts import Entity
from verifact.errors import RetrievalError
from verifact.logging import get_logger
from verifact.retrieval.clients import wikidata
from verifact.retrieval.clients.http import SafeClient

_log = get_logger(__name__)

#: Below this gap between best and second best, surface scoring has not
#: separated the senses.
AMBIGUITY_MARGIN = 0.15

#: Leading determiners are part of the sentence, not of the entity name. spaCy's
#: NER includes them ("The Eiffel Tower"), and Wikidata ranks a different sense
#: first for the determiner-prefixed string.
_ARTICLES = ("the ", "a ", "an ")


def normalize_surface(surface: str) -> str:
    """Strip a leading article and surrounding punctuation for lookup."""
    cleaned = surface.strip().strip("\"'“”’.,")
    lowered = cleaned.lower()
    for article in _ARTICLES:
        if lowered.startswith(article):
            return cleaned[len(article) :]
    return cleaned


@dataclass(frozen=True)
class EntityLink:
    """The result of linking one surface form."""

    surface: str
    #: Best-ranked candidate. Present even when ambiguous, because the caller
    #: resolves ambiguity by relation, not by discarding the ranking.
    qid: str | None
    confidence: float
    candidates: list[str] = field(default_factory=list)
    #: True when surface scoring could not separate the senses. A caller that
    #: cannot disambiguate by context must not return CONTRADICTED.
    ambiguous: bool = False
    reason: str = ""


def _score(candidate: dict[str, str], surface: str, position: int) -> float:
    """Heuristic ranking score.

    Signals, strongest first: exact label match; Wikidata's own result position
    as a relevance prior; and having a description at all, since a bare entity is
    usually a stub.
    """
    label = candidate.get("label", "").strip().lower()
    want = surface.strip().lower()
    score = 0.0
    if label == want:
        score += 0.5
    elif want in label or label in want:
        score += 0.25
    score += 0.4 * (0.6**position)
    if candidate.get("description"):
        score += 0.1
    return round(score, 4)


def link_entity(client: SafeClient, surface: str, limit: int = 5) -> EntityLink:
    """Rank knowledge-base candidates for a surface form."""
    lookup = normalize_surface(surface)
    try:
        candidates = wikidata.search_entities(client, lookup, limit=limit)
    except RetrievalError as exc:
        _log.warning("entity search failed", extra={"surface": surface, "error": str(exc)})
        return EntityLink(surface, None, 0.0, [], False, f"search failed: {exc}")
    if not candidates:
        return EntityLink(surface, None, 0.0, [], False, "no candidates found")

    scored = sorted(
        ((c, _score(c, lookup, i)) for i, c in enumerate(candidates)),
        key=lambda pair: (-pair[1], pair[0]["qid"]),
    )
    qids = [c["qid"] for c, _ in scored]
    best, best_score = scored[0]

    exact = [c for c, _ in scored if c.get("label", "").strip().lower() == lookup.lower()]
    margin_ambiguous = len(scored) > 1 and (best_score - scored[1][1]) < AMBIGUITY_MARGIN
    ambiguous = len(exact) > 1 or margin_ambiguous

    if ambiguous:
        _log.info(
            "ambiguous mention, deferring to relation-based disambiguation",
            extra={"surface": surface, "candidates": qids[:4]},
        )
    return EntityLink(
        surface=surface,
        qid=best["qid"],
        confidence=best_score,
        candidates=qids,
        ambiguous=ambiguous,
        reason=(
            f"{len(exact)} candidates match the label exactly"
            if len(exact) > 1
            else ("top two candidates are within the ambiguity margin" if margin_ambiguous else "")
        ),
    )


def link_claim_entities(client: SafeClient, entities: list[Entity]) -> list[Entity]:
    """Return copies of `entities` with linking results attached.

    `kb_candidates` is populated whenever the mention was ambiguous, so the
    ambiguity reaches the dashboard rather than being resolved out of sight.
    """
    out: list[Entity] = []
    for entity in entities:
        link = link_entity(client, entity.surface)
        out.append(
            entity.model_copy(
                update={
                    "kb_id": link.qid,
                    "kb_confidence": link.confidence,
                    "kb_candidates": link.candidates if link.ambiguous else [],
                }
            )
        )
    return out
