"""Evidence retrieval. Owner: P3. Contract produced: `list[EvidencePassage]`."""

from verifact.retrieval.registry import SourceRegistry, get_registry, load_registry
from verifact.retrieval.retriever import build_query, rank_passages, retrieve_for_claim
from verifact.retrieval.safety import assert_url_is_safe

__all__ = [
    "SourceRegistry",
    "assert_url_is_safe",
    "build_query",
    "get_registry",
    "load_registry",
    "rank_passages",
    "retrieve_for_claim",
]
