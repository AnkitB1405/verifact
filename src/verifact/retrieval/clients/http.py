"""Polite, cached, SSRF-guarded HTTP access.

Owner: P3. Every outbound request in the project goes through `SafeClient`.
Nothing else is allowed to construct an `httpx` client, because then the SSRF
checks and the rate limit would be optional.

Three obligations this discharges:

* **Politeness** (NFR-12): one request per second per source by default, an
  identifying User-Agent, and a cache so a re-run costs nothing. Wikipedia and
  Crossref are free public services and we are a student project.
* **Reproducibility**: a cached response makes a run repeatable and makes the
  evaluation independent of whether a source is up today.
* **Offline operation** (FR-18, NFR-05): with `offline=true` the cache is the
  only source of truth, so the demo works with the network off.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from verifact.config import RetrievalSettings, get_settings
from verifact.errors import RetrievalError
from verifact.logging import get_logger
from verifact.retrieval.registry import SourceRegistry, get_registry
from verifact.retrieval.safety import assert_url_is_safe

_log = get_logger(__name__)

MAX_REDIRECTS = 3


class SafeClient:
    """An HTTP client that can only reach registered hosts."""

    def __init__(
        self,
        settings: RetrievalSettings | None = None,
        registry: SourceRegistry | None = None,
    ) -> None:
        self.cfg = settings or get_settings().retrieval
        self.registry = registry or get_registry()
        self.cache_dir = Path(self.cfg.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_at: dict[str, float] = {}
        self._client: httpx.Client | None = None

    # -- cache ------------------------------------------------------------

    def _cache_path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode()).hexdigest()[:32]
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, url: str) -> dict[str, Any] | None:
        path = self._cache_path(url)
        if not path.exists():
            return None
        try:
            payload: dict[str, Any] = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            # A truncated cache entry is a cache miss, not a crash. It is also
            # not silently ignored: a corrupt cache is worth knowing about.
            _log.warning("discarding unreadable cache entry", extra={"path": str(path)})
            path.unlink(missing_ok=True)
            return None
        return payload

    def _write_cache(self, url: str, payload: dict[str, Any]) -> None:
        tmp = self._cache_path(url).with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(self._cache_path(url))

    # -- fetching ---------------------------------------------------------

    def _throttle(self, host: str) -> None:
        if self.cfg.requests_per_second <= 0:
            return
        min_gap = 1.0 / self.cfg.requests_per_second
        elapsed = time.monotonic() - self._last_request_at.get(host, 0.0)
        if elapsed < min_gap:
            time.sleep(min_gap - elapsed)
        self._last_request_at[host] = time.monotonic()

    def _raw_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.cfg.http_timeout_s,
                headers={"User-Agent": self.cfg.user_agent, "Accept": "application/json"},
                # Redirects are followed by hand so each hop is re-validated
                # against the allowlist; `follow_redirects=True` would hand a
                # permitted host the power to send us anywhere.
                follow_redirects=False,
            )
        return self._client

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET a JSON document, with cache, throttle and safety checks.

        Raises:
            UnsafeUrlError: the URL or a redirect target failed a safety check.
            RetrievalError: offline with no cached copy, a transport failure, a
                non-2xx status, an oversized body, or too many redirects.
        """
        full_url = f"{url}?{urlencode(params)}" if params else url

        cached = self._read_cache(full_url)
        if cached is not None:
            return cached

        if self.cfg.offline:
            raise RetrievalError(f"offline mode and no cached response for {full_url}")

        current = full_url
        for _hop in range(MAX_REDIRECTS + 1):
            host = assert_url_is_safe(current, self.registry)
            self._throttle(host)
            try:
                response = self._raw_client().get(current)
            except httpx.HTTPError as exc:
                raise RetrievalError(f"transport error for {current}: {exc}") from exc

            if response.is_redirect:
                location = response.headers.get("location", "")
                if not location:
                    raise RetrievalError(f"redirect without a location from {current}")
                current = str(httpx.URL(current).join(location))
                continue

            if response.status_code >= 400:
                raise RetrievalError(f"status {response.status_code} from {current}")
            if len(response.content) > self.cfg.max_response_bytes:
                raise RetrievalError(
                    f"response from {current} is {len(response.content)} bytes, "
                    f"over the {self.cfg.max_response_bytes} cap"
                )
            try:
                payload: dict[str, Any] = response.json()
            except ValueError as exc:
                raise RetrievalError(f"non-JSON response from {current}") from exc

            self._write_cache(full_url, payload)
            return payload

        raise RetrievalError(f"too many redirects starting at {full_url}")

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> SafeClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
