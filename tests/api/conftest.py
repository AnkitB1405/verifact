"""API test fixtures. Owner: P1.

Every API test runs against a fresh database on the offline lexical backends, so
the suite needs no network, no model weights and no services, and is
deterministic.

Backend settings are applied with `monkeypatch` inside the fixtures, **not** as
module-level `os.environ` writes. Import-time writes leak into the whole pytest
session: they switched the embedding backend to "lexical" for every other test
file too, which silently broke the dense-retrieval tests in
tests/unit/retrieval. A fixture-scoped change is undone when the test ends.

A temporary **file** database is used rather than `:memory:`. Each SQLite
in-memory connection gets its own private database, and the app's lifespan calls
`init_engine()` again at startup, so tables created by the fixture would not be
visible to the app. A file is shared across connections in the process.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from verifact.api.deps import reset_rate_limits
from verifact.config import get_settings
from verifact.db.models import Base
from verifact.db.session import init_engine

SAMPLE = (
    "The Eiffel Tower was completed in 1950. "
    "The Eiffel Tower is located in Paris. "
    "My neighbours cat is called Mitzi."
)

#: Offline, model-free configuration for the API suite.
OFFLINE_ENV = {
    "VERIFACT_RETRIEVAL__BACKEND": "lexical",
    "VERIFACT_RETRIEVAL__OFFLINE": "true",
    "VERIFACT_VERIFICATION__BACKEND": "lexical",
    "VERIFACT_KG__ENABLED": "false",
}


def _prepare(tmp_path, monkeypatch, auth: bool) -> None:  # type: ignore[no-untyped-def]
    for key, value in OFFLINE_ENV.items():
        monkeypatch.setenv(key, value)
    if auth:
        monkeypatch.setenv("VERIFACT_API__AUTH_ENABLED", "true")
        monkeypatch.setenv("VERIFACT_API__API_KEYS", '["test-key-1"]')
    else:
        monkeypatch.setenv("VERIFACT_API__AUTH_ENABLED", "false")
    url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("VERIFACT_DATABASE_URL", url)
    get_settings.cache_clear()
    Base.metadata.create_all(init_engine(url))
    reset_rate_limits()


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    _prepare(tmp_path, monkeypatch, auth=False)
    from verifact.api.app import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def authed_client(tmp_path, monkeypatch) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    """A client against an instance that actually requires a key."""
    _prepare(tmp_path, monkeypatch, auth=True)
    from verifact.api.app import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()
