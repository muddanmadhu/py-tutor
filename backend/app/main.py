"""FastAPI application factory.

Wires configuration, logging, middleware, error handling and routing. Import
``app`` from here (``uvicorn app.main:app``) or call :func:`create_app` to build
an isolated instance in tests.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from app.api.v1.router import api_router
from app.core.config import ExecutorKind, get_settings
from app.core.errors import AppError, RateLimitError
from app.core.logging import configure_logging, correlation_id, get_logger

logger = get_logger(__name__)

DESCRIPTION = """
**PyForge** — a Python Engineering Mastery Platform.

Learn Python by writing it: interactive lessons, a sandboxed execution engine,
deterministic grading, an adaptive mastery model, an AI mentor with a strict
hint ladder, a project academy and a professional code-review engine.

* Authenticate with `POST /api/auth/login`, then send `Authorization: Bearer <token>`.
* Every error shares one envelope — see the `ErrorResponse` schema.
* Every response carries an `X-Correlation-ID` header; quote it in bug reports.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Registration, login, tokens and profile."},
    {"name": "curriculum", "description": "Courses, modules, lessons and concepts."},
    {"name": "exercises", "description": "Exercises, hints, solutions and submissions."},
    {"name": "execution", "description": "Sandboxed Python execution (the Code Lab)."},
    {"name": "progress", "description": "Mastery, recommendations, badges, certification."},
    {"name": "projects", "description": "The project academy and rubric evaluation."},
    {"name": "ai-tutor", "description": "The AI mentor and its hint policy."},
    {"name": "reference", "description": "Python reference, search, review, interview."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Start-up and shut-down hooks."""
    settings = get_settings()
    configure_logging()
    logger.info(
        "starting %s v%s",
        settings.app_name,
        __version__,
        extra={
            "environment": settings.env.value,
            "executor": settings.executor.value,
            "database": settings.database_url.split("://")[0],
            "ai_backend": "anthropic" if settings.ai_enabled else "offline",
        },
    )
    if settings.executor is ExecutorKind.SUBPROCESS:
        logger.warning(
            "EXECUTOR=subprocess — learner code runs on this host without container "
            "isolation. Never use this outside local development."
        )
    yield
    logger.info("shutting down")


def create_app() -> FastAPI:
    """Build the application."""
    settings = get_settings()
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID", "Server-Timing"],
        max_age=600,
    )

    _register_error_handlers(application)

    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/health", tags=["meta"], summary="Liveness probe")
    def health() -> dict[str, Any]:
        """Report that the process is up."""
        return {"status": "ok", "version": __version__, "environment": settings.env.value}

    @application.get("/ready", tags=["meta"], summary="Readiness probe")
    def ready() -> dict[str, Any]:
        """Report whether dependencies are reachable."""
        from sqlalchemy import text

        from app.db.session import get_engine
        from app.execution.factory import get_executor

        checks: dict[str, bool] = {}
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            checks["database"] = True
        except Exception:  # noqa: BLE001 - readiness must report, not raise
            logger.exception("database readiness check failed")
            checks["database"] = False
        checks["execution_engine"] = get_executor().healthy()

        healthy = all(checks.values())
        return {"status": "ready" if healthy else "degraded", "checks": checks}

    return application


def _register_error_handlers(application: FastAPI) -> None:
    """Install handlers so every failure uses the same envelope."""

    @application.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        headers = {}
        if isinstance(exc, RateLimitError):
            headers["Retry-After"] = str(exc.retry_after_seconds)
        logger.info("handled application error: %s", exc.code, extra={"code": exc.code})
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_payload(correlation_id.get()),
            headers=headers,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
                "problem": error["msg"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "The request body did not validate.",
                    "details": {"fields": fields},
                    "correlation_id": correlation_id.get(),
                }
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": str(exc.detail),
                    "details": {},
                    "correlation_id": correlation_id.get(),
                }
            },
        )

    @application.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        """Never leak internals: log the detail, return an opaque message."""
        logger.exception("unhandled exception: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Something went wrong on our side. The incident has been "
                    "logged — quote the correlation id if you report it.",
                    "details": {},
                    "correlation_id": correlation_id.get(),
                }
            },
        )


app = create_app()
