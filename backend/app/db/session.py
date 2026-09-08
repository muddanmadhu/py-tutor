"""Engine and session factory.

Sessions are request-scoped: one transaction per request, committed on success
and rolled back on any exception. Services never create their own sessions;
they receive one, which keeps transaction boundaries visible at the HTTP layer.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create (once) and return the process-wide SQLAlchemy engine."""
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "echo": settings.database_echo,
        "pool_pre_ping": True,
        "future": True,
    }
    if settings.is_sqlite:
        # SQLite: allow cross-thread use (FastAPI runs sync endpoints in a pool).
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.database_pool_size
        kwargs["max_overflow"] = settings.database_max_overflow

    engine = create_engine(settings.database_url, **kwargs)

    if settings.is_sqlite:

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection: Any, _record: Any) -> None:
            """Enable foreign keys and WAL; SQLite disables FKs by default."""
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped transactional session."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session for scripts, seeding and background work."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose the engine and clear caches. Used by tests between databases."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
