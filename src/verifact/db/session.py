"""Engine and session management.

The engine is created once per process from settings. Tests point
`VERIFACT_DATABASE_URL` at an in-memory SQLite database.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from verifact.config import get_settings

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def init_engine(url: str | None = None, echo: bool = False) -> Engine:
    """Create (or replace) the process engine."""
    global _engine, _factory
    url = url or get_settings().database_url
    kwargs: dict[str, Any] = {"echo": echo, "future": True}
    if url.startswith("sqlite"):
        # Needed so a single in-memory DB is shared across a test's connections.
        kwargs["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        # SQLite does not enforce foreign keys unless asked, which would let the
        # ON DELETE CASCADE rules above silently not apply in dev and tests.
        @event.listens_for(_engine, "connect")
        def _fk_on(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    _factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    return _engine or init_engine()


def _factory_or_init() -> sessionmaker[Session]:
    """Return the session factory, creating the engine on first use.

    A plain `assert` would be stripped by `python -O`, which is exactly the
    configuration where a None factory would surface as an unhelpable
    AttributeError in production.
    """
    if _factory is None:
        init_engine()
    if _factory is None:  # pragma: no cover - init_engine always sets it
        raise RuntimeError("database engine could not be initialised")
    return _factory


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with _factory_or_init()() as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope for background work."""
    session = _factory_or_init()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
