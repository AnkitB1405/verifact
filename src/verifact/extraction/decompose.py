"""Atomic claim decomposition.

Owner: P2. See ADR-002 for the decision to do this with rules rather than an LLM,
and for the operational definition:

    A claim is atomic when it asserts exactly one relation between resolved
    arguments, and removing any part of it destroys the assertion.

Three patterns are implemented, chosen because they cover the great majority of
compound factual sentences:

1. **Clausal coordination** — "X did A and Y did B", "X did A; Y did B".
   Conjoined verbs are split; a conjunct with no subject of its own inherits the
   first clause's subject.
2. **Appositive / relative / participial modifiers** — "The Eiffel Tower,
   completed in 1889, is 330 m tall" yields a separate claim for the modifier.
   These are reconstructed sentences, so `Claim.text` is *not* a substring of the
   source; `char_start`/`char_end` point at the region the claim came from, which
   is what the dashboard highlights.
3. **Coordinated modifiers on one verb** — "won the Nobel Prize in Physics in
   1903 and in Chemistry in 1911" yields one claim per conjunct.

Known limitations, each with a test in `tests/unit/extraction/`:

* No coreference resolution. "He later moved to Berlin" is flagged
  `standalone_interpretable=False` rather than guessed (FR-11). Guessing a
  referent produces a confidently wrong verdict, which is worse than an honest
  AMBIGUOUS.
* Implicit and presupposed claims are not extracted ("the former president" does
  not yield "X was president").
* Nested coordination beyond one level is left as one claim.
* The regex fallback handles only semicolons and ", and"/", but" and is markedly
  weaker than the parse-based path. Which path ran is recorded per run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

#: Pronouns that make a claim non-interpretable on its own.
_DANGLING = frozenset(
    {
        "he",
        "she",
        "it",
        "they",
        "him",
        "her",
        "them",
        "his",
        "hers",
        "its",
        "their",
        "this",
        "that",
        "these",
        "those",
        "there",
    }
)

_CLAUSE_SPLIT_RE = re.compile(r"\s*;\s*|\s*,\s+(?:and|but)\s+(?=\w+\s+\w)")


@dataclass(frozen=True)
class Proposition:
    """One atomic proposition with the source region it came from."""

    text: str
    char_start: int
    char_end: int
    #: True when `text` was rebuilt rather than sliced, so callers know the span
    #: is a provenance pointer and not an exact quotation.
    reconstructed: bool = False
    pattern: str = "whole"


def is_standalone_interpretable(text: str) -> bool:
    """False when the claim opens with, or is dominated by, an unresolved referent.

    Only the leading position is checked. A pronoun later in the sentence usually
    has its antecedent inside the same claim ("Curie won the prize she had been
    nominated for"), whereas a leading pronoun points outside it.
    """
    words = re.findall(r"[\w']+", text.lower())
    if not words:
        return False
    if words[0] in _DANGLING:
        return False
    # "In 1999, he moved" - pronoun subject after a leading adverbial.
    head = words[:6]
    return not any(
        w in _DANGLING
        for w in head[1:3]
        if head[0] in {"in", "on", "by", "later", "then", "afterwards"}
    )


def _subtree_span(tok: Any, exclude_conj: bool = False) -> tuple[int, int]:
    """Character span of a token's subtree.

    With `exclude_conj`, tokens belonging to a conjoined sibling are dropped. A
    preposition's subtree otherwise contains its own conjuncts ("in Physics" owns
    "and in Chemistry"), which makes coordinated groups overlap.
    """
    toks = list(tok.subtree)
    if exclude_conj:
        drop: set[int] = set()
        for child in tok.children:
            if child.dep_ in ("conj", "cc"):
                drop.update(t.i for t in child.subtree)
        toks = [t for t in toks if t.i not in drop] or toks
    return toks[0].idx, toks[-1].idx + len(toks[-1].text)


def _clean(text: str) -> str:
    """Tidy a rebuilt proposition.

    Splitting leaves debris: the coordinator of the clause we removed, and the
    comma that used to delimit a modifier we pulled out. Both have to go, or the
    claim text shown to the user reads as broken English.
    """
    out = re.sub(r"\s+", " ", text).strip()
    out = re.sub(r"\s*,\s*(?=,|\.|;|$)", "", out)  # "Tower, , is" / "Tower ,."
    out = re.sub(r"\s+,\s+", ", ", out)
    # A comma followed by a lowercase word is debris from a removed modifier
    # ("Einstein, developed ..."). Cost: commas inside a list are flattened,
    # which is cosmetic and does not change what is being asserted.
    out = re.sub(r",\s+(?=[a-z])", " ", out)
    out = re.sub(r"\s+(and|but|or)\s*$", "", out, flags=re.I)  # trailing coordinator
    out = re.sub(r"^\s*(and|but|or)\s+", "", out, flags=re.I)
    out = out.strip().strip(",;: ")
    if out and not out.endswith((".", "!", "?")):
        out += "."
    return out[0].upper() + out[1:] if out else out


def _decompose_spacy(sent: Any, offset: int) -> list[Proposition]:
    """Parse-based decomposition over one spaCy sentence span."""
    props: list[Proposition] = []
    sent_start = sent.start_char
    sent_text = sent.text
    root = sent.root

    # --- pattern 2: appositive / relative / participial modifiers -------------
    consumed: list[tuple[int, int]] = []
    for tok in sent:
        if tok.dep_ not in ("appos", "relcl", "acl"):
            continue
        head = tok.head
        if head.pos_ not in ("NOUN", "PROPN"):
            continue
        s, e = _subtree_span(tok)
        mod = sent.doc.text[s:e]
        subject = " ".join(t.text for t in head.subtree if t.i <= head.i and t.dep_ != "punct")
        # "which/who/that" is replaced by the head noun; a bare participle gets "was".
        body = re.sub(r"^(which|who|whom|that)\s+", "", mod, flags=re.I)
        # Unchanged means there was no relative pronoun to strip, so this is a
        # bare participle ("completed in 1889") and needs a copula.
        text = f"{subject} was {body}" if body == mod else f"{subject} {body}"
        props.append(
            Proposition(
                _clean(text),
                s + offset - 0,
                e + offset,
                reconstructed=True,
                pattern=f"modifier:{tok.dep_}",
            )
        )
        consumed.append((s, e))

    # --- pattern 1: clausal coordination -------------------------------------
    verb_conjuncts = [t for t in root.conjuncts if t.pos_ in ("VERB", "AUX")]
    if verb_conjuncts:
        subject = next(
            (
                " ".join(x.text for x in t.subtree)
                for t in root.children
                if t.dep_ in ("nsubj", "nsubjpass")
            ),
            "",
        )
        clauses = [root, *verb_conjuncts]
        for verb in clauses:
            excluded = {i for c in verb_conjuncts if c is not verb for i in range(*_tok_range(c))}
            toks = [
                t
                for t in verb.subtree
                if t.i not in excluded and not (t.dep_ == "cc" and t.head is verb)
            ]
            if not toks:
                continue
            s, e = toks[0].idx, toks[-1].idx + len(toks[-1].text)
            body = sent.doc.text[s:e]
            has_subj = any(c.dep_ in ("nsubj", "nsubjpass") for c in verb.children)
            text = body if has_subj else f"{subject} {body}"
            props.append(
                Proposition(
                    _clean(text),
                    s + offset,
                    e + offset,
                    reconstructed=not has_subj,
                    pattern="clause:conj",
                )
            )
        return props or [
            Proposition(
                _clean(sent_text), sent_start + offset, sent_start + len(sent_text) + offset
            )
        ]

    # --- pattern 3: coordinated modifiers on one verb ------------------------
    pp_groups = _coordinated_modifier_groups(root)
    if pp_groups and len(pp_groups) > 1:
        stem_end = min(g[0][0] for g in pp_groups)
        stem = sent.doc.text[sent_start:stem_end]
        for group in pp_groups:
            mods = " ".join(sent.doc.text[s:e] for s, e in group)
            props.append(
                Proposition(
                    _clean(f"{stem} {mods}"),
                    group[0][0] + offset,
                    group[-1][1] + offset,
                    reconstructed=True,
                    pattern="modifier:coord",
                )
            )
        return props

    # --- fall through: the sentence minus any modifier we already pulled out --
    remainder = sent_text
    for s, e in sorted(consumed, reverse=True):
        rs, re_ = s - sent_start, e - sent_start
        remainder = remainder[:rs] + remainder[re_:]
    remainder = re.sub(r",\s*,", ",", remainder)
    if remainder.strip(" ,.;"):
        props.append(
            Proposition(
                _clean(remainder),
                sent_start + offset,
                sent_start + len(sent_text) + offset,
                reconstructed=bool(consumed),
                pattern="main",
            )
        )
    return props


def _tok_range(tok: Any) -> tuple[int, int]:
    toks = list(tok.subtree)
    return toks[0].i, toks[-1].i + 1


def _coordinated_modifier_groups(root: Any) -> list[list[tuple[int, int]]]:
    """Group a verb's prepositional modifiers into the sets joined by "and".

    "won ... in Physics in 1903 and in Chemistry in 1911" -> two groups of two.

    Grouping is done by the surface position of the coordinator rather than by
    walking the conj chain: spaCy attaches conjoined prepositions inconsistently
    (sometimes under the first preposition, sometimes under its object), and a
    tree walk produced overlapping groups. The coordinator's character position
    is unambiguous.

    Only a single coordinator is handled. Two or more ("A and B and C") is left
    as one claim rather than guessed at - a documented limitation with a test.
    """
    # Prepositional modifiers of the verb AND of its direct object. In
    # "won the Nobel Prize in Physics in 1903 and in Chemistry in 1911" spaCy
    # attaches "in Physics" to Prize and "in 1903" to won, so looking only at the
    # verb's children leaves "in Physics" stuck in the shared stem and the second
    # claim comes out as "in Physics in Chemistry in 1911".
    hosts: list[Any] = [root]
    hosts += [c for c in root.children if c.dep_ in ("dobj", "attr", "nsubjpass")]
    preps = [c for h in hosts for c in h.children if c.dep_ == "prep"]
    if not preps:
        return []

    # Every preposition hanging off the verb, including conjoined ones.
    adps: list[Any] = []
    for prep in preps:
        adps.append(prep)
        adps.extend(t for t in prep.subtree if t.dep_ == "conj" and t.pos_ == "ADP")
    if len(adps) < 2:
        return []

    ccs = [
        t for prep in preps for t in prep.subtree if t.dep_ == "cc" and t.lower_ in ("and", "or")
    ]
    # Deduplicate: overlapping subtrees can surface the same coordinator twice.
    ccs = list({t.i: t for t in ccs}.values())
    if len(ccs) != 1:
        return []
    cc_at = ccs[0].idx

    before: list[tuple[int, int]] = []
    after: list[tuple[int, int]] = []
    for adp in sorted(adps, key=lambda t: t.idx):
        span = _subtree_span(adp, exclude_conj=True)
        (before if span[0] < cc_at else after).append(span)
    if not before or not after:
        return []
    return [before, after]


def decompose(
    sent_text: str,
    char_offset: int,
    spacy_sent: Any | None = None,
) -> list[Proposition]:
    """Split one sentence into atomic propositions.

    Args:
        sent_text: the sentence as it appears in the normalised document.
        char_offset: the sentence's `char_start`, added to every returned span.
        spacy_sent: a parsed spaCy sentence span. When None the regex fallback runs.
    """
    if spacy_sent is not None:
        try:
            return _decompose_spacy(spacy_sent, char_offset - spacy_sent.start_char)
        except (AttributeError, IndexError, ValueError):
            # A parse-shape surprise must degrade to the fallback, not fail a run.
            pass

    parts = [p for p in _CLAUSE_SPLIT_RE.split(sent_text) if p and p.strip()]
    if len(parts) <= 1:
        return [Proposition(_clean(sent_text), char_offset, char_offset + len(sent_text))]
    props: list[Proposition] = []
    cursor = 0
    for part in parts:
        idx = sent_text.find(part, cursor)
        if idx < 0:
            idx = cursor
        props.append(
            Proposition(
                _clean(part),
                char_offset + idx,
                char_offset + idx + len(part),
                pattern="clause:regex",
            )
        )
        cursor = idx + len(part)
    return props
