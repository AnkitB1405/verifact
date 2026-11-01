"""Wikipedia client: search for articles, return passages.

Owner: P3. Tier 2 in the registry: not authoritative, but auditable and
correctable, with a visible revision history.

Passages are paragraphs rather than whole articles or single sentences. A whole
article buries the relevant sentence and blows past the NLI model's input limit;
a single sentence loses the context that makes a claim checkable ("It opened in
1889" needs the paragraph to say what "it" is). A paragraph is the unit the
source itself chose.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from verifact.contracts import EvidencePassage
from verifact.errors import RetrievalError
from verifact.logging import get_logger
from verifact.retrieval.clients.http import SafeClient

_log = get_logger(__name__)

API = "https://en.wikipedia.org/w/api.php"
SOURCE_ID = "wikipedia"

#: Paragraphs shorter than this are headings, stubs or disambiguation noise.
MIN_PARAGRAPH_CHARS = 120


def search_titles(client: SafeClient, query: str, limit: int = 3) -> list[str]:
    payload = client.get_json(
        API,
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "formatversion": "2",
        },
    )
    results = payload.get("query", {}).get("search", [])
    return [r["title"] for r in results if "title" in r]


def fetch_extract(client: SafeClient, title: str) -> tuple[str, date | None, str]:
    """Return (plain-text extract, last-revision date, canonical url)."""
    payload = client.get_json(
        API,
        {
            "action": "query",
            "prop": "extracts|revisions|info",
            "titles": title,
            "explaintext": "1",
            "exsectionformat": "plain",
            "rvprop": "timestamp",
            "inprop": "url",
            "format": "json",
            "formatversion": "2",
        },
    )
    pages = payload.get("query", {}).get("pages", [])
    if not pages:
        raise RetrievalError(f"no wikipedia page for {title!r}")
    page = pages[0]
    if page.get("missing"):
        raise RetrievalError(f"wikipedia page {title!r} is missing")

    published: date | None = None
    revisions = page.get("revisions") or []
    if revisions and revisions[0].get("timestamp"):
        try:
            published = datetime.fromisoformat(
                revisions[0]["timestamp"].replace("Z", "+00:00")
            ).date()
        except ValueError:
            published = None
    url = page.get("fullurl") or f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
    return page.get("extract", ""), published, url


def _paragraphs(extract: str) -> list[str]:
    out = []
    for block in re.split(r"\n{2,}", extract):
        text = re.sub(r"\s+", " ", block).strip()
        # "== History ==" style headings carry no evidence.
        if text.startswith("==") or len(text) < MIN_PARAGRAPH_CHARS:
            continue
        out.append(text)
    return out


def retrieve(
    client: SafeClient,
    claim_id: str,
    query: str,
    max_articles: int = 2,
    max_passages: int = 6,
) -> list[EvidencePassage]:
    """Candidate passages for a query. Ranking happens later, in the retriever."""
    passages: list[EvidencePassage] = []
    try:
        titles = search_titles(client, query, limit=max_articles)
    except RetrievalError as exc:
        # One unreachable source must not fail the run; coverage will reflect it.
        _log.warning("wikipedia search failed", extra={"error": str(exc)})
        return []

    for title in titles:
        try:
            extract, published, url = fetch_extract(client, title)
        except RetrievalError as exc:
            _log.warning("wikipedia extract failed", extra={"title": title, "error": str(exc)})
            continue
        for para in _paragraphs(extract):
            passages.append(
                EvidencePassage(
                    claim_id=claim_id,
                    text=para,
                    source_id=SOURCE_ID,
                    url=url,
                    title=title,
                    published_at=published,
                )
            )
            if len(passages) >= max_passages:
                return passages
    return passages
