"""Crossref client: publication metadata as evidence.

Owner: P3. Tier 3: authoritative for what it covers - a DOI, a title, authors, a
publication date - and silent about everything else. It cannot support a claim
about the *content* of a paper, only about the paper's existence and metadata.
That limit is the reason its tier sits below Wikipedia's for general claims
while being the only usable source for a citation claim.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from verifact.contracts import EvidencePassage
from verifact.errors import RetrievalError
from verifact.logging import get_logger
from verifact.retrieval.clients.http import SafeClient

_log = get_logger(__name__)

API = "https://api.crossref.org/works"
SOURCE_ID = "crossref"


def _published(item: dict[str, Any]) -> date | None:
    parts = (item.get("published") or {}).get("date-parts") or [[]]
    if not parts or not parts[0]:
        return None
    nums = [int(x) for x in parts[0] if isinstance(x, int)]
    if not nums:
        return None
    year = nums[0]
    month = nums[1] if len(nums) > 1 else 1
    day = nums[2] if len(nums) > 2 else 1
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, 1, 1)


def retrieve(
    client: SafeClient, claim_id: str, query: str, limit: int = 3
) -> list[EvidencePassage]:
    """Works matching a query, rendered as one passage of metadata each."""
    try:
        payload = client.get_json(
            API,
            {
                "query.bibliographic": query,
                "rows": limit,
                "select": "title,author,published,DOI,abstract,container-title",
            },
        )
    except RetrievalError as exc:
        _log.warning("crossref query failed", extra={"error": str(exc)})
        return []

    out: list[EvidencePassage] = []
    for item in payload.get("message", {}).get("items", []):
        title = (item.get("title") or [""])[0]
        if not title:
            continue
        authors = ", ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in (item.get("author") or [])[:5]
        )
        venue = (item.get("container-title") or [""])[0]
        doi = item.get("DOI", "")
        abstract = item.get("abstract") or ""
        text = ". ".join(
            part
            for part in [
                f"{title}",
                f"Authors: {authors}" if authors else "",
                f"Published in {venue}" if venue else "",
                f"DOI {doi}" if doi else "",
                abstract.replace("<jats:p>", " ").replace("</jats:p>", " ").strip(),
            ]
            if part
        )
        out.append(
            EvidencePassage(
                claim_id=claim_id,
                text=text,
                source_id=SOURCE_ID,
                url=f"https://doi.org/{doi}" if doi else None,
                title=title,
                published_at=_published(item),
            )
        )
    return out
