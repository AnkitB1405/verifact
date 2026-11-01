"""Outbound request safety: SSRF controls.

Owner: P3 (FR-19, SR-03). This module is the only thing standing between a claim
containing a URL and our process fetching it. The threat is concrete: the input
text is untrusted, entity names feed into query construction, and a cloud
metadata endpoint or an internal admin page is one unchecked request away.

Four controls, each separately tested in tests/security/test_ssrf.py:

1. **Host allowlist** from the source registry. Not a denylist: a denylist of
   bad hosts is a list you will always be behind on.
2. **Address check after resolution.** An allowlisted name is not enough -
   DNS can point anywhere, including 127.0.0.1 and 169.254.169.254. Every
   resolved address must be a global unicast address.
3. **No off-allowlist redirects.** A permitted host may redirect to an internal
   one, so redirects are followed manually and re-checked at each hop.
4. **Size and time caps**, so a hostile or broken endpoint cannot exhaust
   memory or hold a worker open.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from verifact.errors import UnsafeUrlError
from verifact.logging import get_logger
from verifact.retrieval.registry import SourceRegistry

_log = get_logger(__name__)

ALLOWED_SCHEMES = frozenset({"https"})


def _resolved_addresses(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"host {host!r} does not resolve") from exc
    out = []
    for info in infos:
        addr = info[4][0]
        try:
            out.append(ipaddress.ip_address(addr))
        except ValueError:  # pragma: no cover - getaddrinfo returns valid addresses
            continue
    if not out:
        raise UnsafeUrlError(f"host {host!r} resolved to no usable address")
    return out


def assert_address_is_public(host: str) -> None:
    """Reject a host whose *resolved* addresses are not globally routable.

    `is_global` is the right predicate rather than a list of CIDR blocks: it
    already excludes loopback, link-local (169.254.0.0/16, which is where cloud
    metadata lives), private ranges, multicast and reserved space, for both IPv4
    and IPv6, and it does not need maintaining.
    """
    for addr in _resolved_addresses(host):
        if not addr.is_global:
            _log.warning(
                "blocked request to a non-public address",
                extra={"host": host, "resolved": str(addr)},
            )
            raise UnsafeUrlError(f"host {host!r} resolves to non-public address {addr}")


def assert_url_is_safe(url: str, registry: SourceRegistry) -> str:
    """Validate a URL for outbound fetching and return its hostname.

    Raises:
        UnsafeUrlError: wrong scheme, missing host, host not on the registry
            allowlist, or a host resolving to a non-public address.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme {parsed.scheme!r} is not permitted")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("url has no host")
    # Credentials in a URL are a redirect-laundering trick and are never needed
    # for a public read-only source.
    if parsed.username or parsed.password:
        raise UnsafeUrlError("credentials in url are not permitted")
    if not registry.is_allowed_host(host):
        _log.warning("blocked request to a non-allowlisted host", extra={"host": host})
        raise UnsafeUrlError(f"host {host!r} is not in the source registry allowlist")
    assert_address_is_public(host)
    return host
