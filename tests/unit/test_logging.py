"""Logging and redaction tests. Owner: P1 (NFR-15, SR-07)."""

from __future__ import annotations

import json
import logging

from verifact.logging import SENSITIVE_KEYS, RedactionFilter, configure_logging, get_logger


def test_redaction_filter_strips_user_content() -> None:
    """The text being verified is the user's content; it is not an ops log entry."""
    record = logging.LogRecord("t", logging.INFO, "f", 1, "msg", None, None)
    record.text = "my private medical question"  # type: ignore[attr-defined]
    RedactionFilter(enabled=True).filter(record)
    assert record.text == "[redacted]"  # type: ignore[attr-defined]


def test_every_sensitive_key_is_redacted() -> None:
    record = logging.LogRecord("t", logging.INFO, "f", 1, "msg", None, None)
    for key in SENSITIVE_KEYS:
        setattr(record, key, "secret value")
    RedactionFilter(enabled=True).filter(record)
    for key in SENSITIVE_KEYS:
        assert getattr(record, key) == "[redacted]", key


def test_redaction_can_be_disabled_for_local_debugging() -> None:
    record = logging.LogRecord("t", logging.INFO, "f", 1, "msg", None, None)
    record.text = "visible"  # type: ignore[attr-defined]
    RedactionFilter(enabled=False).filter(record)
    assert record.text == "visible"  # type: ignore[attr-defined]


def test_api_key_is_a_sensitive_key() -> None:
    assert "api_key" in SENSITIVE_KEYS


def test_json_logs_are_machine_readable_and_redacted(capsys) -> None:  # type: ignore[no-untyped-def]
    """End to end through the real handler, not just the filter in isolation."""
    configure_logging(level="INFO", json_format=True, redact=True)
    get_logger("test.redaction").info("document built", extra={"text": "SECRET TEXT"})
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(captured)
    assert payload["message"] == "document built"
    assert payload["text"] == "[redacted]"
    assert "SECRET TEXT" not in captured


def test_configure_logging_is_idempotent() -> None:
    """Called at startup and by tests; must not stack handlers."""
    configure_logging(json_format=False)
    first = len(logging.getLogger().handlers)
    configure_logging(json_format=False)
    assert len(logging.getLogger().handlers) == first
