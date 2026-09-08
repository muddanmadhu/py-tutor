"""Application error taxonomy and the RFC 7807-style error envelope.

Every failure the API returns has the same shape, so the frontend has exactly
one error-rendering path:

```json
{
  "error": {
    "code": "exercise_not_found",
    "message": "No exercise with slug 'foo'.",
    "details": {"slug": "foo"},
    "correlation_id": "0f2c..."
  }
}
```
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, client-facing failures.

    Unexpected exceptions are deliberately *not* modelled here: they become a
    500 with no internal detail leaked, and are logged with a stack trace.
    """

    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self, correlation_id: str | None = None) -> dict[str, Any]:
        """Render the error envelope."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "correlation_id": correlation_id,
            }
        }


class ValidationFailure(AppError):  # noqa: N818 - "…Error" would shadow pydantic.ValidationError
    """Input passed schema validation but violates a domain rule."""

    status_code = 422
    code = "validation_failed"


class AuthenticationError(AppError):
    """Credentials are missing or wrong."""

    status_code = 401
    code = "authentication_failed"


class AuthorizationError(AppError):
    """Authenticated, but not permitted."""

    status_code = 403
    code = "not_authorized"


class NotFoundError(AppError):
    """The requested resource does not exist."""

    status_code = 404
    code = "not_found"

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            f"{resource} '{identifier}' was not found.",
            details={"resource": resource, "identifier": str(identifier)},
        )
        self.code = f"{resource.lower().replace(' ', '_')}_not_found"


class ConflictError(AppError):
    """The request conflicts with existing state."""

    status_code = 409
    code = "conflict"


class RateLimitError(AppError):
    """The caller exceeded an allowance."""

    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str, retry_after_seconds: int = 60) -> None:
        super().__init__(message, details={"retry_after_seconds": retry_after_seconds})
        self.retry_after_seconds = retry_after_seconds


class ExecutionError(AppError):
    """The execution engine could not run the submitted code."""

    status_code = 503
    code = "execution_unavailable"


class AIUnavailableError(AppError):
    """The AI tutor backend is unavailable or over budget."""

    status_code = 503
    code = "ai_unavailable"
