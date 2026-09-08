"""HTTP middleware: correlation ids, access logging and security headers."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.logging import correlation_id, get_logger

logger = get_logger("app.access")

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign every request a correlation id and log its outcome.

    The id is accepted from the client when supplied (so a browser session can
    be traced across services) and echoed back on the response, which is what
    makes a learner's bug report actionable: they paste the id, we find the
    exact request.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Wrap one request."""
        incoming = request.headers.get(CORRELATION_HEADER)
        identifier = incoming if incoming and len(incoming) <= 64 else uuid.uuid4().hex
        token = correlation_id.set(identifier)
        request.state.correlation_id = identifier

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise
        finally:
            correlation_id.reset(token)

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers[CORRELATION_HEADER] = identifier
        response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"
        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach conservative security headers to every response.

    The CSP is strict but permits the inline styles and blob workers Monaco
    needs; see ``docs/SECURITY.md`` for why each directive is what it is.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Wrap one request."""
        response = await call_next(request)
        settings = get_settings()

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if request.url.path in {"/docs", "/redoc", "/openapi.json"}:
            return response
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        return response
