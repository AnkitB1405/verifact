"""Claim extraction: the P2 pipeline stage.

`extract_claims(document) -> list[Claim]` is the only entry point the
orchestrator calls. It produces the `claims_golden.json` fixture that P3 and P4
build against (see CONTRIBUTING.md).

Span conventions, which the whole project depends on:

* `Claim.char_start` / `char_end` index into `Document.normalized_text`. For a
  reconstructed claim they point at the *region the claim came from*, so the
  dashboard can highlight it; the text itself is not a substring of that region.
* `Entity` / `TemporalRef` / `NumericRef` spans index into **`Claim.text`**,
  because a reconstructed claim has no exact counterpart in the document.
"""

from __future__ import annotations

from typing import Any

from verifact.config import ExtractionSettings, get_settings
from verifact.contracts import Claim, Document, Entity
from verifact.extraction.checkworthy import classify
from verifact.extraction.decompose import decompose, is_standalone_interpretable
from verifact.extraction.mentions import (
    extract_entities_regex,
    extract_entities_spacy,
    extract_numerics,
    extract_temporal,
)
from verifact.logging import get_logger

_log = get_logger(__name__)


def _load_parser(cfg: ExtractionSettings) -> Any | None:
    """Return a spaCy pipeline, or None to run the dependency-free path."""
    if cfg.backend == "regex":
        return None
    try:
        from verifact.input.processor import _load_spacy

        return _load_spacy(cfg.spacy_model)
    except (ImportError, OSError):
        if cfg.backend == "spacy":
            raise
        _log.warning("spacy unavailable, extraction falling back to regex backend")
        return None


def _entities_for(text: str, parser: Any | None) -> list[Entity]:
    """Entities with spans relative to `text`."""
    if parser is None:
        return extract_entities_regex(text)
    doc = parser(text)
    ents = extract_entities_spacy(doc)
    if ents:
        return ents
    # spaCy found no named entity: fall back to capitalised runs so a claim about
    # a less-famous subject still gets a retrieval query.
    return extract_entities_regex(text)


def extract_claims(
    document: Document,
    settings: ExtractionSettings | None = None,
) -> list[Claim]:
    """Decompose a document into atomic, annotated claims.

    Non-check-worthy claims are returned with `checkworthy=False` rather than
    dropped, so the dashboard can show what was skipped and why. The
    orchestrator is what filters them before retrieval.
    """
    cfg = settings or get_settings().extraction
    parser = _load_parser(cfg)
    max_claims = get_settings().input.max_claims

    parsed_sents: dict[int, Any] = {}
    if parser is not None:
        # Parse the whole document once: the parser is the expensive part, and
        # sentence-at-a-time parsing loses cross-sentence context for free.
        doc = parser(document.normalized_text)
        spans = list(doc.sents)
        for sent in document.sentences:
            match = next((s for s in spans if s.start_char <= sent.char_start < s.end_char), None)
            if match is not None:
                parsed_sents[sent.idx] = match

    claims: list[Claim] = []
    for sent in document.sentences:
        props = decompose(sent.text, sent.char_start, parsed_sents.get(sent.idx))
        for prop in props:
            claim_type, checkworthy = classify(prop.text, parsed_sents.get(sent.idx))
            claims.append(
                Claim(
                    sentence_idx=sent.idx,
                    char_start=max(prop.char_start, 0),
                    char_end=min(prop.char_end, len(document.normalized_text)),
                    text=prop.text,
                    claim_type=claim_type,
                    entities=_entities_for(prop.text, parser),
                    temporal=extract_temporal(prop.text),
                    numerics=extract_numerics(prop.text),
                    checkworthy=checkworthy,
                    standalone_interpretable=is_standalone_interpretable(prop.text),
                )
            )
            if len(claims) >= max_claims:
                _log.warning(
                    "claim cap reached, remaining sentences not decomposed",
                    extra={"cap": max_claims, "doc_id": document.id},
                )
                return claims

    _log.info(
        "claims extracted",
        extra={
            "doc_id": document.id,
            "n_claims": len(claims),
            "n_checkworthy": sum(c.checkworthy for c in claims),
            "backend": "spacy" if parser is not None else "regex",
        },
    )
    return claims
