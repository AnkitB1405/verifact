"""Central exception taxonomy.

Every error the API can return maps to exactly one class here. The handler in
`api.app` turns these into a typed body with no traceback and no echo of the
user's input (FR-52, SR-06).
"""

from __future__ import annotations


class VerifactError(Exception):
    """Base class. `code` is the stable string clients match on."""

    code = "internal_error"
    http_status = 500
    #: Safe to show a client. Never interpolate user input or source content into it.
    public_message = "An internal error occurred."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.public_message)
        #: Full detail for the log only, never for the response body.
        self.detail = detail


class InputValidationError(VerifactError):
    code = "invalid_input"
    http_status = 422
    public_message = "The submitted text failed validation."


class InputTooLargeError(InputValidationError):
    code = "input_too_large"
    public_message = "The submitted text exceeds the configured maximum length."


class SourceNotRegisteredError(VerifactError):
    code = "source_not_registered"
    http_status = 400
    public_message = "The requested source is not in the configured registry."


class UnsafeUrlError(VerifactError):
    """Raised by the SSRF guard. The blocked URL goes to the log, not the response."""

    code = "unsafe_url"
    http_status = 400
    public_message = "The requested URL is not permitted."


class RetrievalError(VerifactError):
    code = "retrieval_failed"
    http_status = 502
    public_message = "An evidence source could not be reached."


class ModelUnavailableError(VerifactError):
    code = "model_unavailable"
    http_status = 503
    public_message = "A required model backend is unavailable."


class RunNotFoundError(VerifactError):
    code = "run_not_found"
    http_status = 404
    public_message = "No such analysis run."


class RateLimitedError(VerifactError):
    code = "rate_limited"
    http_status = 429
    public_message = "Too many requests."


class AuthError(VerifactError):
    code = "unauthorized"
    http_status = 401
    public_message = "A valid API key is required."
