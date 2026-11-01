"""Regenerate P3's golden fixtures from live sources.

    python -m tests.fixtures._generate_p3_fixtures

Run deliberately, commit the result in the same PR as the change that moved it
(CONTRIBUTING.md). P4's aggregation tests read these files so they never depend
on a live API.
"""

from __future__ import annotations

import json
from pathlib import Path

from verifact.extraction import extract_claims
from verifact.input import build_document
from verifact.kg import check_claim
from verifact.retrieval.clients.http import SafeClient
from verifact.retrieval.retriever import retrieve_for_claim

HERE = Path(__file__).parent

SOURCE_TEXT = (
    "The Eiffel Tower is located in Paris. "
    "The Eiffel Tower is located in Berlin. "
    "The Eiffel Tower was completed in 1889. "
    "The Eiffel Tower is 330 metres tall. "
    "Marie Curie won the Nobel Prize in Physics in 1903. "
    "Python was created by Guido van Rossum. "
    "Water boils at 100 degrees Celsius."
)


def main() -> None:
    claims = [c for c in extract_claims(build_document(SOURCE_TEXT)) if c.checkworthy]
    evidence: list[dict[str, object]] = []
    kgchecks: list[dict[str, object]] = []

    with SafeClient() as client:
        for claim in claims:
            passages = retrieve_for_claim(claim, client, top_k=3)
            evidence.append(
                {
                    "claim_text": claim.text,
                    "passages": [
                        {
                            "text": p.text,
                            "source_id": p.source_id,
                            "url": p.url,
                            "title": p.title,
                            "published_at": p.published_at.isoformat() if p.published_at else None,
                            "scores": {
                                "bm25": round(p.scores.bm25, 4)
                                if p.scores.bm25 is not None
                                else None,
                                "dense": round(p.scores.dense, 4)
                                if p.scores.dense is not None
                                else None,
                                "rrf": round(p.scores.rrf, 6),
                                "relevance": round(p.scores.relevance, 4),
                            },
                        }
                        for p in passages
                    ],
                }
            )
            check = check_claim(claim, client)
            kgchecks.append(
                {
                    "claim_text": claim.text,
                    "status": check.status.value,
                    "triples_checked": [
                        {
                            "subject": t.subject,
                            "predicate": t.predicate,
                            "object": t.object,
                            "subject_qid": t.subject_qid,
                        }
                        for t in check.triples_checked
                    ],
                    "path_evidence": check.path_evidence,
                    "notes": check.notes,
                }
            )

    comment = (
        "Golden fixture owned by P3. Consumed by P4's aggregation and weighting "
        "tests so they never call a live API. Regenerate with "
        "`python -m tests.fixtures._generate_p3_fixtures`."
    )
    (HERE / "evidence_golden.json").write_text(
        json.dumps({"_comment": comment, "source_text": SOURCE_TEXT, "claims": evidence}, indent=2)
        + "\n"
    )
    (HERE / "kgcheck_golden.json").write_text(
        json.dumps({"_comment": comment, "source_text": SOURCE_TEXT, "claims": kgchecks}, indent=2)
        + "\n"
    )
    print(f"wrote evidence_golden.json ({sum(len(e['passages']) for e in evidence)} passages)")
    print(f"wrote kgcheck_golden.json ({len(kgchecks)} checks)")


if __name__ == "__main__":
    main()
