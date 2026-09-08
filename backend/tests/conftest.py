"""Shared pytest fixtures.

Every test runs against a fresh in-memory-backed SQLite database and the
subprocess executor, so the suite needs no Docker daemon and no PostgreSQL. The
Docker path is covered separately by tests marked ``@pytest.mark.docker``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

# Configure before anything imports app.core.config, whose settings are cached.
os.environ.update(
    {
        "PYFORGE_ENV": "test",
        "PYFORGE_DEBUG": "true",
        "PYFORGE_SECRET_KEY": "test-only-secret-key-that-is-long-enough-1234567890",
        "PYFORGE_EXECUTOR": "subprocess",
        "PYFORGE_EXEC_TIMEOUT_SECONDS": "8",
        "PYFORGE_LOG_LEVEL": "WARNING",
        "PYFORGE_ANTHROPIC_API_KEY": "",
        "PYFORGE_REDIS_URL": "",
    }
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db, get_engine, get_session_factory, reset_engine  # noqa: E402
from app.execution.factory import get_executor, get_rate_limiter  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _configure_settings() -> Iterator[None]:
    """Ensure settings are read from the test environment."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def database_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """A file-backed SQLite database per test.

    File-backed rather than ``:memory:`` because the API and the test share a
    connection pool; an in-memory database would give each connection its own
    empty schema.
    """
    path = tmp_path_factory.mktemp("db") / "test.db"
    return f"sqlite+pysqlite:///{path}"


@pytest.fixture()
def session(database_url: str) -> Iterator[Session]:
    """A transactional session against a freshly-created schema."""
    os.environ["PYFORGE_DATABASE_URL"] = database_url
    get_settings.cache_clear()
    reset_engine()

    Base.metadata.create_all(bind=get_engine())
    factory = get_session_factory()
    db = factory()
    try:
        yield db
        db.commit()
    finally:
        db.close()
        reset_engine()


@pytest.fixture()
def seeded_session(session: Session) -> Session:
    """A session with the full seed curriculum loaded."""
    from app.db.init_db import seed_all

    seed_all(session)
    session.commit()
    return session


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    """An API client sharing the test's database session."""
    app = create_app()

    def _override_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = _override_db
    get_rate_limiter().reset()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_client(seeded_session: Session) -> Iterator[TestClient]:
    """An API client against a seeded database."""
    app = create_app()

    def _override_db() -> Iterator[Session]:
        yield seeded_session

    app.dependency_overrides[get_db] = _override_db
    get_rate_limiter().reset()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def user(session: Session) -> User:
    """A registered learner."""
    from app.services.auth import AuthService

    created = AuthService(session).register(
        email="learner@example.com",
        password="a-strong-test-password-1",
        display_name="Test Learner",
    )
    session.commit()
    return created


@pytest.fixture()
def auth_headers(user: User) -> dict[str, str]:
    """Authorization header for ``user``."""
    from app.services.auth import AuthService

    tokens = AuthService.issue_tokens(user)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest.fixture()
def executor():  # type: ignore[no-untyped-def]
    """The configured execution backend (subprocess, in tests)."""
    get_executor.cache_clear()
    return get_executor()
