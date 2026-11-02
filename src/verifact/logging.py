"""Structured logging with redaction.

Two requirements drive this module:

* Logs must be machine-readable, so a run can be traced across stages.
* Logs must not contain the user's raw input text at INFO or above (NFR-15,
  SR-07). The text being verified is the user's content; it does not belong in
  an operations log.

Redaction is a filter on the logging pipeline rather than a convention at call
sites, because a convention will be broken by whoever adds the next log line.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

from pythonjsonlogger.json import JsonFormatter

#: Record attributes whose values are considered user content.
SENSITIVE_KEYS = frozenset(
    {"text", "raw_text", "normalized_text", "claim_text", "passage_text", "api_key"}
)
_REDACTED = "[redacted]"


class RedactionFilter(logging.Filter):
    """Replace user content in structured extras with a placeholder.

    A short preview length is deliberately *not* offered: a 40-character preview
    of a medical question is still the user's medical question.
    """

    def __init__(self, enabled: bool = True) -> None:
        super().__init__()
        self.enabled = enabled

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.enabled:
            return True
        for key in SENSITIVE_KEYS:
            if hasattr(record, key):
                setattr(record, key, _REDACTED)
        return True


def configure_logging(level: str = "INFO", json_format: bool = True, redact: bool = True) -> None:
    """Install handlers on the root logger. Idempotent."""
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)

    handler: logging.Handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(
            JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s",
                rename_fields={"asctime": "ts", "levelname": "level"},
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s | %(message)s")
        )

    handler.addFilter(RedactionFilter(enabled=redact))
    root.addHandler(handler)
    root.setLevel(level)
    # Third-party libraries are noisy at DEBUG and leak URLs we do not want logged.
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(max(logging.WARNING, root.level))


class ContextAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter that *merges* call-site extras with its own context.

    `logging.LoggerAdapter.process` replaces `kwargs["extra"]` with the
    adapter's own mapping. Using the stock adapter therefore discarded every
    `extra={...}` passed at the call site - so the structured fields this
    project logs were silently dropped, and the redaction filter never saw the
    keys it exists to redact. Merging is the whole reason this subclass exists.
    """

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        merged = {**(self.extra or {}), **(kwargs.get("extra") or {})}
        kwargs["extra"] = merged
        return msg, kwargs


def get_logger(name: str, **context: Any) -> ContextAdapter:
    """Logger carrying fixed structured context, e.g. a run id."""
    return ContextAdapter(logging.getLogger(name), context)
