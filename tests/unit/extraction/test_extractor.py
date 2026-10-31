"""End-to-end extraction tests and golden-fixture regeneration. Owner: P2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from verifact.contracts import ClaimType
from verifact.extraction import extract_claims
from verifact.input import build_document

SAMPLE = (
    "The Eiffel Tower, completed in 1889, is 330 metres tall. "
    "Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911. "
    "I think it is the most beautiful monument in Europe. "
    "Should we visit it? "
    "Install the package before running the demo. "
    "He later moved to Berlin."
)


@pytest.fixture
def claims():  # type: ignore[no-untyped-def]
    return extract_claims(build_document(SAMPLE))


def test_claim_spans_point_into_the_document(claims) -> None:  # type: ignore[no-untyped-def]
    """FR-10: every claim must be locatable in the normalised text."""
    doc = build_document(SAMPLE)
    for claim in claims:
        assert 0 <= claim.char_start < claim.char_end <= len(doc.normalized_text)


def test_mention_spans_are_relative_to_claim_text(claims) -> None:  # type: ignore[no-untyped-def]
    """Documented span convention: mentions index into Claim.text, not the document.

    A reconstructed claim has no exact counterpart in the source, so a mention
    span into the document would be meaningless for it.
    """
    for claim in claims:
        for mention in [*claim.entities, *claim.temporal, *claim.numerics]:
            assert claim.text[mention.char_start : mention.char_end] == mention.surface


def test_claims_map_back_to_their_sentence(claims) -> None:  # type: ignore[no-untyped-def]
    doc = build_document(SAMPLE)
    for claim in claims:
        assert 0 <= claim.sentence_idx < len(doc.sentences)


def test_non_checkworthy_claims_are_kept_not_dropped(claims) -> None:  # type: ignore[no-untyped-def]
    """The dashboard has to be able to show what was skipped and why."""
    skipped = [c for c in claims if not c.checkworthy]
    assert skipped, "opinions and questions should be present but flagged"
    assert {c.claim_type for c in skipped} <= {
        ClaimType.OPINION,
        ClaimType.QUESTION,
        ClaimType.INSTRUCTION,
        ClaimType.RHETORICAL,
    }


def test_unresolved_referent_is_flagged(claims) -> None:  # type: ignore[no-untyped-def]
    """FR-11: 'He later moved to Berlin' must not get a guessed subject."""
    berlin = [c for c in claims if "Berlin" in c.text]
    assert berlin
    assert all(c.standalone_interpretable is False for c in berlin)


def test_claim_cap_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    from verifact.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings.input, "max_claims", 3)
    assert len(extract_claims(build_document(SAMPLE))) <= 3


def test_regex_backend_produces_valid_claims() -> None:
    """The dependency-free path must satisfy the same contracts."""
    from verifact.config import ExtractionSettings

    doc = build_document(SAMPLE, extraction_settings=ExtractionSettings(backend="regex"))
    claims = extract_claims(doc, ExtractionSettings(backend="regex"))
    assert claims
    for claim in claims:
        assert claim.text
        assert 0 <= claim.char_start < claim.char_end <= len(doc.normalized_text)


@pytest.mark.ml
def test_golden_fixture_matches_current_output() -> None:
    """P3 and P4 build against this file; drift must fail CI, not surprise them.

    Regenerate deliberately with:
        python -m tests.unit.extraction.test_extractor
    and commit the result in the same PR as the decomposer change (CONTRIBUTING).
    """
    path = Path(__file__).parents[2] / "fixtures" / "claims_golden.json"
    golden = json.loads(path.read_text())
    produced = [
        {
            "text": c.text,
            "claim_type": c.claim_type.value,
            "checkworthy": c.checkworthy,
            "standalone_interpretable": c.standalone_interpretable,
            "entities": [e.surface for e in c.entities],
            "temporal": [t.iso for t in c.temporal],
            "numerics": [n.surface for n in c.numerics],
        }
        for c in extract_claims(build_document(golden["source_text"]))
    ]
    assert produced == golden["claims"], "decomposer output drifted from the golden fixture"


def _regenerate() -> None:
    path = Path(__file__).parents[2] / "fixtures" / "claims_golden.json"
    claims = extract_claims(build_document(SAMPLE))
    payload = {
        "_comment": (
            "Golden fixture owned by P2. Consumed by P3 (retrieval, entity linking) and "
            "P4 (aggregation tests). Regenerate with "
            "`python -m tests.unit.extraction.test_extractor` and commit in the same PR "
            "as the change that moved it."
        ),
        "source_text": SAMPLE,
        "claims": [
            {
                "text": c.text,
                "claim_type": c.claim_type.value,
                "checkworthy": c.checkworthy,
                "standalone_interpretable": c.standalone_interpretable,
                "entities": [e.surface for e in c.entities],
                "temporal": [t.iso for t in c.temporal],
                "numerics": [n.surface for n in c.numerics],
            }
            for c in claims
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {path} with {len(claims)} claims")


if __name__ == "__main__":
    _regenerate()
