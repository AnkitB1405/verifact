"""Input processing tests. Owner: P2.

The offset invariant is the single most important property in the project: every
highlight, every claim span and every annotated output is built on it, and a
violation is invisible until the dashboard underlines the wrong words.
"""

from __future__ import annotations

import pytest

from verifact.contracts import Document
from verifact.errors import InputTooLargeError, InputValidationError
from verifact.input import build_document, normalize_text, split_sentences

TEXTS = [
    "Water boils at 100 degrees Celsius.",
    "Dr. Smith joined CERN in 1999. He later moved to Berlin, e.g. for the MPI.",
    "The Eiffel Tower is 330 metres tall! Is it taller than the Shard? Probably not.",
    "Line one.\n\nLine two is a separate paragraph.",
    'She said "it is fine." Then she left.',
    "A single sentence without terminal punctuation",
    "Multiple    spaces\tand\ttabs collapse. So do   unicode spaces.",
    "U.S. policy changed in 2020. The U.K. followed in 2021.",
]


@pytest.mark.parametrize("text", TEXTS)
def test_offset_invariant(text: str) -> None:
    """FR-03, FR-04: slicing the normalised text must reproduce each sentence."""
    doc = build_document(text)
    for sentence in doc.sentences:
        assert doc.normalized_text[sentence.char_start : sentence.char_end] == sentence.text


@pytest.mark.parametrize("text", TEXTS)
def test_sentences_are_ordered_and_non_overlapping(text: str) -> None:
    doc = build_document(text)
    spans = [(s.char_start, s.char_end) for s in doc.sentences]
    assert spans == sorted(spans)
    for (_, prev_end), (next_start, _) in zip(spans, spans[1:], strict=False):
        assert prev_end <= next_start, "sentence spans must not overlap"


@pytest.mark.parametrize("text", ["", "   ", "\n\n\t", None])
def test_empty_rejected(text: str | None) -> None:
    """FR-02: a typed validation error, never a 500."""
    with pytest.raises(InputValidationError):
        build_document(text)  # type: ignore[arg-type]


def test_max_length_enforced_on_raw_text() -> None:
    """FR-01, SR-05: reject before doing any work on a hostile payload."""
    from verifact.config import InputSettings

    with pytest.raises(InputTooLargeError):
        build_document("a. " * 100, input_settings=InputSettings(max_chars=50))


def test_max_sentences_enforced() -> None:
    from verifact.config import InputSettings

    with pytest.raises(InputTooLargeError):
        build_document("A thing happened. " * 20, input_settings=InputSettings(max_sentences=5))


def test_abbreviations_do_not_split() -> None:
    doc = build_document("Dr. Smith met Prof. Jones in Jan. 2020. They agreed.")
    assert len(doc.sentences) == 2, [s.text for s in doc.sentences]


def test_normalization_is_idempotent() -> None:
    """Normalising twice must not move offsets; the pipeline relies on it."""
    once = normalize_text("Café  —  résumé\r\nnext")
    assert normalize_text(once) == once


def test_unicode_nfkc_applied() -> None:
    # Full-width digits would otherwise never match a retrieved passage.
    assert "2020" in normalize_text("Published in ２０２０")


def test_raw_text_is_preserved_unmodified() -> None:
    raw = "  Messy\r\n\r\n\r\ninput.  "
    doc = build_document(raw)
    assert doc.raw_text == raw, "raw_text is the audit trail and must not be rewritten"


def test_document_is_immutable() -> None:
    doc = build_document("A fact.")
    with pytest.raises(Exception, match="frozen|immutable"):
        doc.normalized_text = "tampered"  # type: ignore[misc]


def test_regex_backend_matches_invariant_without_spacy() -> None:
    """The dependency-free path must satisfy the same invariant."""
    from verifact.config import ExtractionSettings

    text = normalize_text("One thing. Two things! Three? Four.")
    sentences = split_sentences(text, ExtractionSettings(backend="regex"))
    assert len(sentences) == 4
    for s in sentences:
        assert text[s.char_start : s.char_end] == s.text


def test_builds_a_document_contract() -> None:
    doc = build_document("A fact.")
    assert isinstance(doc, Document)
    assert doc.sentences[0].idx == 0
