"""Persistence. SQLAlchemy ORM only — no string-built SQL anywhere (SR-04)."""

from verifact.db.session import get_session, init_engine, session_scope

__all__ = ["get_session", "init_engine", "session_scope"]
