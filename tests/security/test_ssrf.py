"""SSRF controls. Owner: P3 (SR-03, FR-19).

The retrieval module is the only part of the system that makes outbound
requests, and its inputs are derived from untrusted text. Each test here names
the attack it blocks.

No network is needed: every case is rejected before a socket is opened, except
the DNS-rebinding case which only resolves a name.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from verifact.errors import UnsafeUrlError
from verifact.retrieval.registry import load_registry
from verifact.retrieval.safety import assert_address_is_public, assert_url_is_safe


@pytest.fixture(scope="module")
def registry():  # type: ignore[no-untyped-def]
    return load_registry(Path("config/sources.yaml"))


ATTACKS = [
    # (url, what it is trying to do)
    ("https://127.0.0.1/admin", "loopback by literal IP"),
    ("https://localhost/admin", "loopback by name"),
    ("https://[::1]/admin", "loopback over IPv6"),
    ("https://169.254.169.254/latest/meta-data/", "cloud instance metadata service"),
    ("https://10.0.0.5/internal", "RFC1918 private range"),
    ("https://192.168.1.1/router", "home/office private range"),
    ("https://172.16.0.10/internal", "RFC1918 private range, second block"),
    ("https://0.0.0.0/", "unspecified address"),
    ("https://evil.example.com/payload", "host absent from the registry allowlist"),
    ("http://en.wikipedia.org/wiki/X", "plaintext scheme downgrade"),
    ("file:///etc/passwd", "non-HTTP scheme"),
    ("ftp://en.wikipedia.org/x", "non-HTTP scheme on an allowed host"),
    ("https://user:secret@en.wikipedia.org/x", "credentials smuggled into the URL"),
    ("https:///nohost", "missing host"),
]


@pytest.mark.parametrize(("url", "attack"), ATTACKS)
def test_attack_is_blocked(url: str, attack: str, registry) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(UnsafeUrlError):
        assert_url_is_safe(url, registry)


@pytest.mark.parametrize(
    "url",
    [
        "https://en.wikipedia.org/w/api.php",
        "https://www.wikidata.org/w/api.php",
        "https://api.crossref.org/works",
    ],
)
@pytest.mark.network
def test_registered_hosts_are_allowed(url: str, registry) -> None:  # type: ignore[no-untyped-def]
    """The guard must not be so strict that nothing works."""
    assert assert_url_is_safe(url, registry)


@pytest.mark.network
def test_allowlisted_name_resolving_to_a_private_address_is_blocked() -> None:
    """DNS rebinding: an allowlisted *name* is not enough.

    An attacker who controls DNS for a permitted hostname, or any public name
    with a private A record, would otherwise reach internal services. The check
    therefore runs on the resolved address, not on the string.
    `localhost` stands in for such a name: it is a public name with a loopback
    address, which is exactly the shape of the attack.
    """
    with pytest.raises(UnsafeUrlError):
        assert_address_is_public("localhost")


def test_unresolvable_host_is_rejected_not_passed_through() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_address_is_public("this-host-does-not-exist.invalid")


def test_registry_is_the_single_allowlist(registry) -> None:  # type: ignore[no-untyped-def]
    """There is no second, separate list to forget to update."""
    assert registry.allowed_hosts
    for host in registry.allowed_hosts:
        assert registry.is_allowed_host(host)
