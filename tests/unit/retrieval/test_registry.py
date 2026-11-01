"""Source registry tests. Owner: P3."""

from __future__ import annotations

from pathlib import Path

import pytest

from verifact.contracts import SourceKind
from verifact.errors import SourceNotRegisteredError
from verifact.retrieval.registry import UNKNOWN_SOURCE_ID, load_registry

REGISTRY = Path("config/sources.yaml")


@pytest.fixture(scope="module")
def registry():  # type: ignore[no-untyped-def]
    return load_registry(REGISTRY)


def test_registry_loads_expected_sources(registry) -> None:  # type: ignore[no-untyped-def]
    assert {"wikidata", "wikipedia", "crossref", "local_corpus", "unknown"} <= set(
        registry.source_ids
    )


def test_unknown_source_gets_lowest_tier_not_rejected(registry) -> None:  # type: ignore[no-untyped-def]
    """FR-14: an unregistered source is down-weighted, never silently dropped.

    Dropping it would hide a coverage gap from the evaluation; trusting it would
    break the closed-registry rule.
    """
    source = registry.get("some-blog-nobody-vetted")
    assert source.id == UNKNOWN_SOURCE_ID
    assert source.reliability_tier == 5
    assert source.kind is SourceKind.UNKNOWN


def test_tiers_are_ordered_so_weighting_is_monotonic(registry) -> None:  # type: ignore[no-untyped-def]
    """A better tier must never have lower base reliability than a worse one."""
    pairs = sorted(
        (registry.get(sid).reliability_tier, registry.get(sid).base_reliability)
        for sid in registry.source_ids
    )
    reliabilities = [r for _, r in pairs]
    assert reliabilities == sorted(reliabilities, reverse=True), pairs


def test_host_allowlist_is_derived_from_the_registry(registry) -> None:
    """FR-13/FR-19: the registry is also the SSRF allowlist - one source of truth."""
    assert "en.wikipedia.org" in registry.allowed_hosts
    assert registry.for_host("en.wikipedia.org").id == "wikipedia"
    assert not registry.is_allowed_host("evil.example.com")


def test_host_match_is_case_insensitive(registry) -> None:
    assert registry.is_allowed_host("EN.Wikipedia.ORG")


def test_missing_registry_file_fails_loudly(tmp_path: Path) -> None:
    """Starting with an empty registry would retrieve nothing while looking healthy."""
    with pytest.raises(SourceNotRegisteredError):
        load_registry(tmp_path / "nope.yaml")


def test_empty_registry_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text("sources: []\n")
    with pytest.raises(SourceNotRegisteredError):
        load_registry(path)


def test_halflife_none_means_no_decay(registry) -> None:  # type: ignore[no-untyped-def]
    """Crossref metadata does not become less true with age."""
    assert registry.get("crossref").halflife_days is None
