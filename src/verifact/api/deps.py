"""API dependencies: authentication and rate limiting.

Owner: P1 (FR-50, FR-51, SR-05).

Dependencies are declared with `Annotated[..., Depends(...)]` rather than as
argument defaults. Both work in FastAPI; the annotated form is the current
idiom and keeps a call out of a default value, which linters rightly object to.

The rate limiter is an in-process fixed-window counter. That is the honest
choice for the single-process deployment of ADR-004, and the limitation is
documented rather than hidden: with more than one worker each keeps its own
counter, so the effective limit multiplies by the worker count. Running more
than one process is the migration trigger for a shared store - not a reason to
add Redis today.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, Header, Request

from verifact.config import Settings, get_settings
from verifact.errors import AuthError, RateLimitedError
from verifact.logging import get_logger

_log = get_logger(__name__)

#: key -> (epoch minute of the window, requests seen in it)
_WINDOWS: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]
ApiKeyHeader = Annotated[str | None, Header(alias="X-API-Key")]


def require_api_key(settings: SettingsDep, x_api_key: ApiKeyHeader = None) -> str:
    """Validate the API key and return the calling principal.

    With auth disabled every caller is the shared "anonymous" principal, which
    the rate limiter then buckets by client address - so a development instance
    is still protected from a runaway client.
    """
    if not settings.api.auth_enabled:
        return "anonymous"
    if not x_api_key or x_api_key not in settings.api.api_keys:
        # The attempted key is deliberately not logged. A mistyped real key is
        # still a secret, and logging it would copy it into an operations system.
        _log.warning("rejected request with a missing or invalid api key")
        raise AuthError
    return x_api_key


PrincipalDep = Annotated[str, Depends(require_api_key)]


def enforce_rate_limit(request: Request, settings: SettingsDep, principal: PrincipalDep) -> str:
    """Fixed-window per-principal rate limit (FR-51)."""
    limit = settings.api.rate_limit_per_minute
    if principal != "anonymous":
        key = principal
    else:
        key = request.client.host if request.client else "unknown"

    minute = int(time.time() // 60)
    window, count = _WINDOWS[key]
    if window != minute:
        _WINDOWS[key] = (minute, 1)
        return principal
    if count >= limit:
        raise RateLimitedError(f"limit of {limit} requests per minute exceeded")
    _WINDOWS[key] = (window, count + 1)
    return principal


CallerDep = Annotated[str, Depends(enforce_rate_limit)]


def reset_rate_limits() -> None:
    """Clear the counters. Used by tests; never called by the application."""
    _WINDOWS.clear()
