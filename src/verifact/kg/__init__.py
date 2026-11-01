"""Knowledge graph verification. Owner: P3. Contract produced: `KGCheck`."""

from verifact.kg.consistency import check_claim
from verifact.kg.linking import EntityLink, link_claim_entities, link_entity
from verifact.kg.predicates import get_predicates, load_predicates
from verifact.kg.subgraph import build_subgraph, labelled_path, reaches

__all__ = [
    "EntityLink",
    "build_subgraph",
    "check_claim",
    "get_predicates",
    "labelled_path",
    "link_claim_entities",
    "link_entity",
    "load_predicates",
    "reaches",
]
