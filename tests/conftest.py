"""Shared test configuration.

The environment is set before `verifact.config` is imported anywhere, because
settings are cached for the process and auth refuses to start without keys.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("VERIFACT_API__AUTH_ENABLED", "false")
os.environ.setdefault("VERIFACT_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("VERIFACT_ENVIRONMENT", "test")

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def has_spacy() -> bool:
    try:
        import spacy

        spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        return False
    return True


@pytest.fixture
def claims_golden() -> list[dict[str, Any]]:
    """P2's golden fixture, consumed by P3 and P4 tests."""
    return json.loads((FIXTURES / "claims_golden.json").read_text())["claims"]
