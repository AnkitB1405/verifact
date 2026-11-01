"""The source registry: which sources are permitted, and how much they are worth.

Owner: P3. Consumed by P4's weighting stage, which multiplies every passage by
its source's reliability.

The registry is *closed* (FR-13). That is the brief's hard rule and the main
structural difference from RARR (`gao2023rarr`), which post-edits using whatever
a web search returns. An unknown source resolves to the `unknown` tier rather
than being discarded, because a silent drop hides a coverage gap from the
evaluation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from verifact.contracts import Source, SourceKind
from verifact.errors import SourceNotRegisteredError
from verifact.logging import get_logger

_log = get_logger(__name__)

#: Id used for anything not in the registry.
UNKNOWN_SOURCE_ID = "unknown"


class SourceRegistry:
    """Loaded source definitions plus the host allowlist derived from them."""

    def __init__(self, sources: dict[str, Source], hosts: dict[str, str]) -> None:
        self._sources = sources
        #: hostname -> source id. This is also the SSRF allowlist (FR-19), so the
        #: registry is the single place that decides what may be contacted.
        self._hosts = hosts

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(self._sources)

    @property
    def allowed_hosts(self) -> frozenset[str]:
        return frozenset(self._hosts)

    def get(self, source_id: str) -> Source:
        """Return a source definition, falling back to the `unknown` tier.

        Raises:
            SourceNotRegisteredError: when even `unknown` is absent, which means
                the registry file itself is malformed.
        """
        if source_id in self._sources:
            return self._sources[source_id]
        if UNKNOWN_SOURCE_ID not in self._sources:
            raise SourceNotRegisteredError(
                f"source {source_id!r} is not registered and no 'unknown' tier is defined"
            )
        _log.warning(
            "unregistered source, assigned the lowest tier",
            extra={"source_id": source_id},
        )
        return self._sources[UNKNOWN_SOURCE_ID]

    def for_host(self, host: str) -> Source:
        """Map a hostname to its source definition."""
        return self.get(self._hosts.get(host.lower(), UNKNOWN_SOURCE_ID))

    def is_allowed_host(self, host: str) -> bool:
        return host.lower() in self._hosts


def load_registry(path: Path) -> SourceRegistry:
    """Parse the registry file.

    Raises:
        SourceNotRegisteredError: the file is missing or has no sources. Starting
            with an empty registry would mean retrieving nothing while looking
            healthy, so this fails loudly.
    """
    if not path.exists():
        raise SourceNotRegisteredError(f"source registry not found at {path}")
    raw: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    entries = raw.get("sources") or []
    if not entries:
        raise SourceNotRegisteredError(f"source registry at {path} defines no sources")

    defaults = raw.get("defaults") or {}
    sources: dict[str, Source] = {}
    hosts: dict[str, str] = {}
    for entry in entries:
        source = Source(
            id=entry["id"],
            name=entry["name"],
            kind=SourceKind(entry["kind"]),
            reliability_tier=int(entry["reliability_tier"]),
            base_reliability=float(entry["base_reliability"]),
            halflife_days=entry.get("halflife_days", defaults.get("halflife_days")),
        )
        sources[source.id] = source
        for host in entry.get("hosts") or []:
            hosts[host.lower()] = source.id

    _log.info(
        "source registry loaded",
        extra={"n_sources": len(sources), "n_hosts": len(hosts)},
    )
    return SourceRegistry(sources, hosts)


@lru_cache(maxsize=4)
def get_registry(path: Path | None = None) -> SourceRegistry:
    """Cached registry. Tests call `get_registry.cache_clear()`."""
    from verifact.config import get_settings

    return load_registry(path or get_settings().retrieval.registry_path)
