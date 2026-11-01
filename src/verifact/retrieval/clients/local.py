"""Local corpus client.

Owner: P3. Tier 4: trust equals whatever the operator's curation is worth, so it
ranks below anything with public review.

Two jobs. It is the mechanism for verifying against private or institutional
documents, and it is how the test suite exercises retrieval with no network
(FR-18) - the same code path, a different source.

Format: one JSON Lines file, one object per passage:

    {"text": "...", "title": "...", "url": "...", "published_at": "2020-01-31"}
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from verifact.contracts import EvidencePassage
from verifact.logging import get_logger

_log = get_logger(__name__)

SOURCE_ID = "local_corpus"


def load_corpus(path: Path) -> list[dict[str, str]]:
    """Read a JSONL corpus. A malformed line is skipped and counted, not fatal."""
    if not path.exists():
        return []
    docs: list[dict[str, str]] = []
    skipped = 0
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if isinstance(obj, dict) and obj.get("text"):
            docs.append(obj)
        else:
            skipped += 1
    if skipped:
        _log.warning("skipped malformed corpus lines", extra={"path": str(path), "n": skipped})
    return docs


def to_passages(docs: list[dict[str, str]], claim_id: str) -> list[EvidencePassage]:
    out: list[EvidencePassage] = []
    for doc in docs:
        published: date | None = None
        if doc.get("published_at"):
            try:
                published = date.fromisoformat(str(doc["published_at"]))
            except ValueError:
                published = None
        out.append(
            EvidencePassage(
                claim_id=claim_id,
                text=str(doc["text"]),
                source_id=SOURCE_ID,
                url=doc.get("url"),
                title=doc.get("title"),
                published_at=published,
            )
        )
    return out
