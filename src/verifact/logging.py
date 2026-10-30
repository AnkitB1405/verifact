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


def get_logger(name: str, **context: Any) -> logging.LoggerAdapter[logging.Logger]:
    """Logger carrying fixed structured context, e.g. a run id."""
    return logging.LoggerAdapter(logging.getLogger(name), context)
