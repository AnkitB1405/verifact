"""Wikidata client: entity search and statement retrieval.

Owner: P3. Tier 1 in the registry: structured, versioned, and individual
statements carry references.

Deliberately uses the MediaWiki entity API (`wbsearchentities`,
`wbgetentities`) rather than the SPARQL endpoint. `wbgetentities` returns an
entity's full statement set in one cached call, which *is* a one-hop
neighbourhood - exactly what the subgraph builder needs. SPARQL would mean a
hand-written query per predicate pattern, a second response format, and a
network round trip per check, for no extra information. Recorded in ADR-003.
"""

from __future__ import annotations

from typing import Any

from verifact.errors import RetrievalError
from verifact.logging import get_logger
from verifact.retrieval.clients.http import SafeClient

_log = get_logger(__name__)

API = "https://www.wikidata.org/w/api.php"
SOURCE_ID = "wikidata"


def search_entities(client: SafeClient, label: str, limit: int = 5) -> list[dict[str, str]]:
    """Candidate entities for a surface form.

    Returns a list, never a single pick: "Washington" is a person, a state and a
    city, and choosing silently is the failure FR-21 exists to prevent.
    """
    payload = client.get_json(
        API,
        {
            "action": "wbsearchentities",
            "search": label,
            "language": "en",
            "uselang": "en",
            "limit": limit,
            "format": "json",
        },
    )
    out = []
    for hit in payload.get("search", []):
        out.append(
            {
                "qid": hit.get("id", ""),
                "label": hit.get("label", ""),
                "description": hit.get("description", ""),
                "match": hit.get("match", {}).get("text", ""),
            }
        )
    return [c for c in out if c["qid"]]


def fetch_entity(client: SafeClient, qid: str) -> dict[str, Any]:
    """Raw entity document for a QID."""
    payload = client.get_json(
        API,
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims|labels|descriptions",
            "languages": "en",
            "format": "json",
        },
    )
    entities = payload.get("entities", {})
    if qid not in entities or "missing" in entities.get(qid, {}):
        raise RetrievalError(f"wikidata entity {qid} not found")
    entity: dict[str, Any] = entities[qid]
    return entity


def label_of(entity: dict[str, Any]) -> str:
    return str(entity.get("labels", {}).get("en", {}).get("value", ""))


def statements(entity: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Flatten an entity's claims into `{property_id: [value, ...]}`.

    Each value is `{"type": ..., "qid"/"text"/"time": ...}`. Only preferred and
    normal rank statements are kept: a deprecated statement records something
    Wikidata has decided is wrong, so treating it as evidence would be a bug.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for pid, claim_list in (entity.get("claims") or {}).items():
        values: list[dict[str, Any]] = []
        for claim in claim_list:
            if claim.get("rank") == "deprecated":
                continue
            snak = claim.get("mainsnak", {})
            if snak.get("snaktype") != "value":
                # "no value" / "unknown value" are assertions of absence and
                # must not be read as a value.
                continue
            value = snak.get("datavalue", {}).get("value")
            dtype = snak.get("datavalue", {}).get("type")
            if dtype == "wikibase-entityid" and isinstance(value, dict):
                values.append({"type": "entity", "qid": value.get("id", "")})
            elif dtype == "time" and isinstance(value, dict):
                values.append({"type": "time", "time": str(value.get("time", ""))})
            elif dtype == "quantity" and isinstance(value, dict):
                values.append({"type": "quantity", "amount": str(value.get("amount", ""))})
            elif dtype == "string":
                values.append({"type": "string", "text": str(value)})
            elif dtype == "monolingualtext" and isinstance(value, dict):
                values.append({"type": "string", "text": str(value.get("text", ""))})
        if values:
            out[pid] = values
    return out
