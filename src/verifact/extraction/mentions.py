"""Entity, date and number extraction.

Owner: P2. Consumed by P3 for query construction and entity linking, so the
character spans here must point into `Document.normalized_text` — P3 slices them.

Two backends. spaCy's NER is the real one; the regex fallback exists so the
package is usable and testable without a model download, and it is deliberately
conservative: it would rather miss a mention than invent one, because a
hallucinated entity becomes a hallucinated retrieval query.
"""

from __future__ import annotations

import re
from datetime import date

from verifact.contracts import Entity, NumericRef, TemporalRef

_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december"
    "|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)

# Dates: ISO, "12 March 1999", "March 12, 1999", bare 4-digit years, decades, centuries.
_DATE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("iso", r"\b(\d{4})-(\d{2})-(\d{2})\b"),
    ("dmy", rf"\b(\d{{1,2}})\s+({_MONTHS})\.?,?\s+(\d{{4}})\b"),
    ("mdy", rf"\b({_MONTHS})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b"),
    ("my", rf"\b({_MONTHS})\.?\s+(\d{{4}})\b"),
    ("decade", r"\b(\d{3}0)s\b"),
    ("year", r"\b(1\d{3}|20\d{2}|21\d{2})\b"),
)
_DATE_RE = re.compile("|".join(f"(?P<{name}>{pat})" for name, pat in _DATE_PATTERNS), re.I)

_MONTH_NUM = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}

# Numbers with an optional unit. Percentages and currency are kept as units so
# "40%" and "40 metres" are not conflated by the verification stage.
_NUMBER_RE = re.compile(
    r"(?P<num>[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-+]?\d+(?:\.\d+)?)"
    r"(?:\s*(?P<unit>%|percent|per cent|°C|°F|degrees?|km|kilometres?|kilometers?|m\b|metres?|"
    r"meters?|cm|mm|miles?|ft|feet|inches|kg|kilograms?|g\b|grams?|lbs?|pounds?|tonnes?|tons?|"
    r"s\b|seconds?|minutes?|hours?|days?|weeks?|months?|years?|USD|EUR|GBP|INR|\$|€|£|₹|"
    r"million|billion|trillion|thousand))?",
    re.I,
)

#: Capitalised runs, used only by the fallback. Sentence-initial words are
#: excluded because every sentence starts capitalised and would otherwise
#: produce a spurious entity on every single sentence.
_PROPER_RE = re.compile(
    r"\b([A-Z][\w'’\-]*"
    r"(?:\s+(?:of|de|van|von|the)\s+[A-Z][\w'’\-]*)?"  # connector needs a capital after it
    r"(?:\s+[A-Z][\w'’\-]*)*)"
)


def _parse_iso(kind: str, text: str) -> str | None:
    """Best-effort ISO-8601 for a matched date. None when not confidently parseable."""
    t = text.strip().rstrip(".,")
    try:
        if kind == "iso":
            return date.fromisoformat(t).isoformat()
        if kind == "year":
            return f"{int(t):04d}"
        if kind == "decade":
            return f"{int(t[:4]):04d}"  # "1990s" -> 1990, precision loss is recorded by kind
        low = t.lower().replace(",", " ")
        parts = [p for p in re.split(r"[\s.]+", low) if p]
        month = next((_MONTH_NUM[p[:3]] for p in parts if p[:3] in _MONTH_NUM), None)
        year = next((int(p) for p in parts if p.isdigit() and len(p) == 4), None)
        day = next((int(p) for p in parts if p.isdigit() and len(p) <= 2), None)
        if month and year:
            return date(year, month, day or 1).isoformat() if day else f"{year:04d}-{month:02d}"
    except (ValueError, KeyError, StopIteration):
        return None
    return None


def extract_temporal(text: str, offset: int = 0) -> list[TemporalRef]:
    """Dates and years, with ISO where parseable.

    `offset` is added to every span so a caller working on a sentence slice gets
    spans into the whole document.
    """
    out: list[TemporalRef] = []
    taken: list[tuple[int, int]] = []
    for m in _DATE_RE.finditer(text):
        kind = m.lastgroup or ""
        s, e = m.span()
        # Longer patterns are listed first; skip a bare year already covered by
        # a full date match so "12 March 1999" is one reference, not two.
        if any(s >= ts and e <= te for ts, te in taken):
            continue
        taken.append((s, e))
        out.append(
            TemporalRef(
                surface=m.group(0),
                iso=_parse_iso(kind, m.group(0)),
                char_start=s + offset,
                char_end=e + offset,
            )
        )
    return out


def extract_numerics(text: str, offset: int = 0) -> list[NumericRef]:
    """Numbers with units. Years are skipped: they are temporal, not quantities."""
    out: list[NumericRef] = []
    years = {(t.char_start - offset, t.char_end - offset) for t in extract_temporal(text)}
    for m in _NUMBER_RE.finditer(text):
        s, e = m.span()
        raw = m.group("num")
        unit = (m.group("unit") or "").strip() or None
        # Any overlap with a temporal span means this is a date, not a quantity.
        # Containment is not enough: "1960s" matches as 1960 with unit "s"
        # (seconds), which extends past the decade span by one character.
        if any(s < ye and e > ys for ys, ye in years):
            continue
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        out.append(
            NumericRef(
                surface=m.group(0).strip(),
                value=value,
                unit=unit,
                char_start=s + offset,
                char_end=e + offset,
            )
        )
    return out


def extract_entities_spacy(span: object, offset: int = 0) -> list[Entity]:
    """Entities from a spaCy span or doc.

    Dates and cardinals are dropped here because `extract_temporal` and
    `extract_numerics` handle them with explicit parsing; keeping both would
    give the KG stage two disagreeing views of the same mention.
    """
    skip = {"DATE", "TIME", "CARDINAL", "ORDINAL", "PERCENT", "QUANTITY", "MONEY"}
    out: list[Entity] = []
    for ent in span.ents:  # type: ignore[attr-defined]
        if ent.label_ in skip:
            continue
        out.append(
            Entity(
                surface=ent.text,
                char_start=ent.start_char + offset,
                char_end=ent.end_char + offset,
                label=ent.label_,
            )
        )
    return out


def extract_entities_regex(
    text: str, offset: int = 0, skip_first_word: bool = True
) -> list[Entity]:
    """Fallback entity extraction: capitalised runs, conservatively.

    Labelled `PROPN` rather than a guessed type, because this backend has no
    basis for deciding PERSON vs ORG vs GPE and a guessed label would mislead
    the knowledge-graph stage into querying the wrong predicate.
    """
    out: list[Entity] = []
    for m in _PROPER_RE.finditer(text):
        s, e = m.span(1)
        surface = m.group(1).strip()
        # Strip a leading article so "The Eiffel Tower" links as "Eiffel Tower".
        for article in ("The ", "A ", "An "):
            if surface.startswith(article):
                surface = surface[len(article) :]
                s += len(article)
                break
        # A lone capitalised word at position 0 is probably just sentence case,
        # not a proper noun. A multi-word run is worth keeping either way.
        if skip_first_word and s == 0 and " " not in surface:
            continue
        if len(surface) < 2 or surface.lower() in {"the", "a", "an", "i"}:
            continue
        out.append(
            Entity(
                surface=surface,
                char_start=s + offset,
                char_end=s + offset + len(surface),
                label="PROPN",
            )
        )
    return out
