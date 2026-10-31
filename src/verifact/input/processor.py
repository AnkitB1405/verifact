"""Validation, normalisation and sentence splitting.

The invariant this module exists to guarantee (FR-03, FR-04):

    document.normalized_text[s.char_start:s.char_end] == s.text

for every sentence. Everything downstream — claim spans, annotated output,
highlighted problem spans in the dashboard — is built on offsets into
`normalized_text`, so if this slips, the UI highlights the wrong words and no
test further down will notice.

Normalisation therefore happens *once*, before splitting, and offsets are only
ever taken against the normalised string. We never normalise again later.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

from verifact.config import ExtractionSettings, InputSettings, get_settings
from verifact.contracts import Document, Sentence
from verifact.errors import InputTooLargeError, InputValidationError
from verifact.logging import get_logger

_log = get_logger(__name__)

#: Abbreviations whose trailing period does not end a sentence. Deliberately
#: short: a long list is a dictionary problem, and spaCy is the real answer when
#: it is installed. Every entry here is one we hit in test text.
_ABBREVIATIONS = frozenset(
    {
        "mr",
        "mrs",
        "ms",
        "dr",
        "prof",
        "sr",
        "jr",
        "st",
        "mt",
        "vs",
        "etc",
        "e.g",
        "i.e",
        "approx",
        "fig",
        "no",
        "vol",
        "pp",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "sept",
        "oct",
        "nov",
        "dec",
        "u.s",
        "u.k",
        "a.m",
        "p.m",
        "ph.d",
        "b.sc",
        "m.sc",
    }
)

#: A sentence boundary: terminal punctuation, optional closing quote/bracket,
#: whitespace, then something that can start a sentence.
_BOUNDARY = re.compile(r'(?<=[.!?])(["\')\]]*)(\s+)(?=["\'(\[]*[A-Z0-9])')

_WS_RUN = re.compile(r"[ \t  -   　]+")
_NEWLINE_RUN = re.compile(r"\n{3,}")


def normalize_text(text: str, settings: InputSettings | None = None) -> str:
    """Normalise without changing meaning.

    NFKC folds compatibility forms (ligatures, full-width digits) so that
    retrieval and string matching behave; it can change string *length*, which
    is exactly why offsets are taken after this step and never before.
    """
    cfg = settings or get_settings().input
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    if cfg.normalize_unicode:
        out = unicodedata.normalize("NFKC", out)
    # Collapse horizontal whitespace runs but keep paragraph structure: a
    # paragraph break is information a sentence splitter can use.
    out = _WS_RUN.sub(" ", out)
    out = _NEWLINE_RUN.sub("\n\n", out)
    return out.strip()


def _ends_with_abbreviation(chunk: str) -> bool:
    tail = chunk.rstrip()
    if not tail.endswith("."):
        return False
    last = tail[:-1].split()[-1].lower() if tail[:-1].split() else ""
    last = last.strip("(\"'[")
    return last in _ABBREVIATIONS or (len(last) == 1 and last.isalpha())


def _split_offsets(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of sentences, trimmed of surrounding space."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        end = m.end(1)  # include a closing quote/bracket in the sentence
        if _ends_with_abbreviation(text[start:end]):
            continue
        if text[start:end].strip():
            spans.append((start, end))
        start = m.end()
    if text[start:].strip():
        spans.append((start, len(text)))

    # Trim whitespace inside each span so the invariant holds on a .strip()ed
    # sentence text rather than forcing the caller to remember to strip.
    trimmed: list[tuple[int, int]] = []
    for s, e in spans:
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            trimmed.append((s, e))
    return trimmed


def _spacy_split_offsets(text: str, model_name: str) -> list[tuple[int, int]] | None:
    """Sentence spans from spaCy, or None when the model is not installed.

    Returning None rather than raising lets the caller fall back; a missing
    optional model must not take the pipeline down.
    """
    try:
        import spacy
    except ImportError:
        return None
    try:
        nlp = _load_spacy(model_name)
    except OSError:
        _log.warning("spacy model not installed, using regex splitter", extra={"model": model_name})
        return None
    doc = nlp(text)
    spans = [(s.start_char, s.end_char) for s in doc.sents]
    out: list[tuple[int, int]] = []
    for s, e in spans:
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            out.append((s, e))
    del spacy
    return out


_SPACY_CACHE: dict[str, Any] = {}


def _load_spacy(model_name: str) -> Any:
    """Load and cache a spaCy pipeline. Loading costs ~1s, so never per request."""
    if model_name not in _SPACY_CACHE:
        import spacy

        # Only the components we need: the parser is what produces sentence
        # boundaries and the dependency tree extraction later relies on.
        _SPACY_CACHE[model_name] = spacy.load(model_name, exclude=["lemmatizer", "textcat"])
    return _SPACY_CACHE[model_name]


def split_sentences(
    normalized: str,
    settings: ExtractionSettings | None = None,
) -> list[Sentence]:
    """Split normalised text into sentences carrying exact offsets.

    Backend `auto` prefers spaCy and falls back to the regex splitter, so the
    package installs and the tests run without a 450 MB model download.
    """
    cfg = settings or get_settings().extraction
    spans: list[tuple[int, int]] | None = None
    if cfg.backend in ("spacy", "auto"):
        spans = _spacy_split_offsets(normalized, cfg.spacy_model)
        if spans is None and cfg.backend == "spacy":
            raise InputValidationError("spaCy backend requested but the model is unavailable")
    if spans is None:
        spans = _split_offsets(normalized)

    return [
        Sentence(idx=i, char_start=s, char_end=e, text=normalized[s:e])
        for i, (s, e) in enumerate(spans)
    ]


def build_document(
    raw_text: str,
    asof: date | None = None,
    input_settings: InputSettings | None = None,
    extraction_settings: ExtractionSettings | None = None,
) -> Document:
    """Validate, normalise and split. The entry point for the pipeline.

    Raises:
        InputValidationError: empty or whitespace-only input (FR-02).
        InputTooLargeError: beyond the configured character or sentence cap (FR-01).
    """
    cfg = input_settings or get_settings().input
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise InputValidationError("input text is empty or whitespace only")
    if len(raw_text) > cfg.max_chars:
        # Length is checked on the raw text as well, so a hostile input cannot
        # force us to normalise 50 MB before we are allowed to reject it (SR-05).
        raise InputTooLargeError(f"input is {len(raw_text)} chars, limit is {cfg.max_chars}")

    normalized = normalize_text(raw_text, cfg)
    if not normalized:
        raise InputValidationError("input normalised to an empty string")

    sentences = split_sentences(normalized, extraction_settings)
    if len(sentences) > cfg.max_sentences:
        raise InputTooLargeError(
            f"input has {len(sentences)} sentences, limit is {cfg.max_sentences}"
        )

    doc = Document(raw_text=raw_text, normalized_text=normalized, sentences=sentences, asof=asof)
    _log.info("document built", extra={"doc_id": doc.id, "n_sentences": len(sentences)})
    return doc
