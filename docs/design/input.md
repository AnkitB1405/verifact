# Input Processing

**Owner:** P2 (Bhuvi) · **Code:** `src/verifact/input/` · **Requirements:** FR-01…FR-06
**Produces:** `Document`

## What it does

Takes raw text, validates it, normalises it once, and splits it into sentences
that carry exact character offsets into the normalised text.

## Why it exists

To guarantee one invariant:

```
document.normalized_text[s.char_start:s.char_end] == s.text
```

Every claim span, every highlighted problem span in the dashboard, and the whole
annotated-output feature are built on offsets into `normalized_text`. If this
slips by one character, the dashboard underlines the wrong words — and **no test
further down the pipeline would notice**, because every later stage would be
internally consistent with the wrong offsets. The module exists to make that
failure impossible rather than unlikely.

## How it works internally

1. **Validate before working.** Length is checked against `max_chars` on the
   *raw* string. A 50 MB payload is rejected before anything normalises it
   (SR-05). Empty or whitespace-only input raises `InputValidationError`.
2. **Normalise exactly once.** Line endings are unified, NFKC is applied,
   horizontal whitespace runs are collapsed, and three-or-more newlines become a
   paragraph break. NFKC can *change string length* — full-width `２０２０`
   becomes `2020` — which is precisely why offsets are taken afterwards and the
   text is never normalised again later.
3. **Split.** spaCy's parser is preferred; a regex splitter is the fallback. Both
   return `(start, end)` spans which are then trimmed of surrounding whitespace,
   so the invariant holds on stripped sentence text without the caller having to
   remember to strip.
4. **Cap.** Sentence count is checked against `max_sentences`.

The regex splitter looks for terminal punctuation, optional closing quotes or
brackets, whitespace, then a capital or digit — and rejects the boundary if the
preceding chunk ends in a known abbreviation or a single initial.

## What alternatives exist

| Alternative | Why not |
|---|---|
| NLTK `punkt` | another dependency and another model download for a job spaCy already does |
| Naive `text.split(".")` | breaks on "Dr.", "e.g.", "U.S.", decimals and ellipses |
| spaCy only, no fallback | a 450 MB model download would become mandatory, and CI would need it |
| Offsets into the *raw* text | normalisation changes length, so raw offsets drift from the text every later stage reads |

## What could go wrong

- **spaCy and the regex splitter disagree** on sentence boundaries, so claim ids
  differ between a machine with the `ml` extra and one without. Mitigated by the
  run recording which backend was used; not eliminated.
- **Abbreviation list is finite.** A sentence ending in an unlisted abbreviation
  splits wrongly. The list holds only forms we actually hit in test text; a
  dictionary-scale list is a different problem.
- **Unicode direction overrides and zero-width characters** survive
  normalisation. They cannot break the offset invariant, but they can make
  displayed text differ from stored text.
- **Language is not detected.** Non-English input is processed as if it were
  English (A-03 in the SRS), producing nonsense claims rather than an error.

## How it is tested

`tests/unit/input/test_processor.py`, 29 tests. The offset invariant is
property-tested over eight text shapes (abbreviations, quotes, paragraph breaks,
mixed newlines, unicode spaces, no terminal punctuation). Separate tests assert
spans are ordered and non-overlapping, that normalisation is idempotent, that
`raw_text` is preserved byte-for-byte as the audit trail, and that the
dependency-free path satisfies the same invariant.
