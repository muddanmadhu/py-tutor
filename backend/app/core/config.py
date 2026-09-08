"""Application configuration.

All settings are environment-driven with the ``PYFORGE_`` prefix so the same
image runs unchanged in development, test and production. Settings are read
once and cached; nothing else in the codebase reads ``os.environ`` directly.
"""

from __future__ import annotations

import secrets
from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class ExecutorKind(StrEnum):
    """Which execution backend runs learner code."""

    DOCKER = "docker"
    SUBPROCESS = "subprocess"
    #: No server-side sandbox at all: the client runs the code itself (Pyodide
    #: in the browser) and reports the result back for grading. Safe to run in
    #: production precisely because untrusted code never reaches the server —
    #: the cost is that grading input is client-supplied and therefore forgeable.
    CLIENT = "client"


_INSECURE_SECRETS = {
    "change-me-in-production-this-value-is-not-secret",
    "dev-only-secret-change-me",
    "secret",
    "changeme",
}


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="PYFORGE_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- Application -------------------------------------------------------
    env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    app_name: str = "PyForge"
    api_v1_prefix: str = "/api"
    log_level: str = "INFO"
    log_json: bool = False

    # --- Security ----------------------------------------------------------
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_ttl_minutes: Annotated[int, Field(ge=1, le=1440)] = 30
    refresh_token_ttl_days: Annotated[int, Field(ge=1, le=90)] = 14
    #: ``NoDecode`` stops pydantic-settings JSON-decoding this from the
    #: environment. Without it, the documented comma-separated form
    #: (``a.example.com,b.example.com``) raises before ``_split_origins`` can
    #: run, because the source layer tries ``json.loads`` on complex types first.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    password_min_length: Annotated[int, Field(ge=8)] = 10
    #: When set, bearer tokens are verified as Firebase ID tokens instead of
    #: tokens this application issued, and accounts are provisioned on first
    #: sign-in. The project id is public — it is not a credential.
    firebase_project_id: str | None = None

    # --- Persistence -------------------------------------------------------
    database_url: str = "sqlite+pysqlite:///./pyforge.db"
    database_echo: bool = False
    database_pool_size: Annotated[int, Field(ge=1, le=100)] = 10
    database_max_overflow: Annotated[int, Field(ge=0, le=100)] = 20
    redis_url: str | None = "redis://localhost:6379/0"

    # --- Execution engine --------------------------------------------------
    executor: ExecutorKind = ExecutorKind.DOCKER
    runner_image: str = "pyforge/runner:latest"
    exec_timeout_seconds: Annotated[float, Field(gt=0, le=120)] = 10.0
    exec_memory_mb: Annotated[int, Field(ge=32, le=2048)] = 256
    exec_cpus: Annotated[float, Field(gt=0, le=4)] = 0.5
    exec_pids_limit: Annotated[int, Field(ge=8, le=512)] = 64
    exec_max_output_bytes: Annotated[int, Field(ge=1024, le=4 * 1024 * 1024)] = 65536
    exec_max_files: Annotated[int, Field(ge=1, le=200)] = 25
    exec_max_source_bytes: Annotated[int, Field(ge=1024, le=4 * 1024 * 1024)] = 262144
    exec_max_concurrent: Annotated[int, Field(ge=1, le=128)] = 8
    exec_rate_limit_per_minute: Annotated[int, Field(ge=1, le=600)] = 60

    # --- AI tutor ----------------------------------------------------------
    anthropic_api_key: str | None = None
    ai_model: str = "claude-sonnet-5"
    ai_max_tokens: Annotated[int, Field(ge=128, le=8192)] = 1200
    ai_daily_message_limit: Annotated[int, Field(ge=1)] = 200
    ai_request_timeout_seconds: Annotated[float, Field(gt=0)] = 45.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string as well as a list."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return upper

    @model_validator(mode="after")
    def _enforce_production_invariants(self) -> Settings:
        """Fail fast on configurations that are unsafe in production."""
        if self.env is not Environment.PRODUCTION:
            return self
        problems: list[str] = []
        if self.secret_key in _INSECURE_SECRETS or len(self.secret_key) < 32:
            problems.append("PYFORGE_SECRET_KEY must be a unique value of 32+ characters")
        if self.debug:
            problems.append("PYFORGE_DEBUG must be false")
        if self.executor is ExecutorKind.SUBPROCESS:
            problems.append(
                "PYFORGE_EXECUTOR must be 'docker' or 'client' (subprocess is dev-only)"
            )
        if self.database_url.startswith("sqlite"):
            problems.append("SQLite is not supported in production; use PostgreSQL")
        if any(origin == "*" for origin in self.cors_origins):
            problems.append("wildcard CORS origin is not allowed")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        """Whether this process is running in production."""
        return self.env is Environment.PRODUCTION

    @property
    def is_sqlite(self) -> bool:
        """Whether the configured database is SQLite."""
        return self.database_url.startswith("sqlite")

    @property
    def client_side_execution(self) -> bool:
        """Whether learner code runs in the browser rather than on the server."""
        return self.executor is ExecutorKind.CLIENT

    @property
    def firebase_auth_enabled(self) -> bool:
        """Whether identity comes from Firebase rather than local passwords."""
        return bool(self.firebase_project_id)

    @property
    def ai_enabled(self) -> bool:
        """Whether a live model backs the AI tutor."""
        return bool(self.anthropic_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
