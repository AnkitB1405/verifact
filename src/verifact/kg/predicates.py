"""Claim-to-triple predicate mapping.

Owner: P3 (FR-23). The supported predicate set is data, not code, so adding a
relation is a config change reviewed as such - and so the set is enumerable when
an examiner asks "what exactly can your knowledge graph check?".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from verifact.logging import get_logger

_log = get_logger(__name__)

ValueType = Literal["entity", "time", "quantity"]


@dataclass(frozen=True)
class Predicate:
    """One checkable relation."""

    name: str
    pids: tuple[str, ...]
    value_type: ValueType
    transitive: bool
    patterns: tuple[re.Pattern[str], ...]
    tolerance: float = 0.0

    def matches(self, text: str) -> bool:
        return self.match_span(text) is not None

    def match_span(self, text: str) -> tuple[int, int] | None:
        """Character span of the relation phrase, used to split subject/object."""
        for pattern in self.patterns:
            found = pattern.search(text)
            if found:
                return found.span()
        return None


@dataclass(frozen=True)
class PredicateMap:
    predicates: tuple[Predicate, ...]

    def find(self, claim_text: str) -> Predicate | None:
        """First predicate whose surface pattern matches.

        First match, not best match: the patterns are mutually distinctive, and a
        scoring scheme here would be unexplainable complexity for no gain. If two
        ever genuinely compete, the fix is to make the patterns narrower.
        """
        for predicate in self.predicates:
            if predicate.matches(claim_text):
                return predicate
        return None

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.predicates)


def load_predicates(path: Path) -> PredicateMap:
    if not path.exists():
        _log.warning(
            "predicate map missing, kg checks will be NOT_APPLICABLE", extra={"path": str(path)}
        )
        return PredicateMap(())
    raw = yaml.safe_load(path.read_text()) or {}
    out: list[Predicate] = []
    for entry in raw.get("predicates") or []:
        out.append(
            Predicate(
                name=entry["name"],
                pids=tuple(entry["pids"]),
                value_type=entry["value_type"],
                transitive=bool(entry.get("transitive", False)),
                patterns=tuple(re.compile(p, re.I) for p in entry.get("patterns") or []),
                tolerance=float(entry.get("tolerance", 0.0)),
            )
        )
    _log.info("predicate map loaded", extra={"n_predicates": len(out)})
    return PredicateMap(tuple(out))


@lru_cache(maxsize=4)
def get_predicates(path: Path | None = None) -> PredicateMap:
    from verifact.config import get_settings

    return load_predicates(path or get_settings().kg.supported_predicates_path)
