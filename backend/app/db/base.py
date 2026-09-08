"""Declarative base and shared column conventions.

A single naming convention is applied to every constraint so Alembic can
autogenerate stable, reversible migrations (unnamed constraints are the usual
cause of migrations that cannot be downgraded).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Timezone-aware current time. Never use naive datetimes in this codebase."""
    return datetime.now(UTC)


def new_uuid() -> str:
    """Generate a primary key.

    UUID4 hex strings keep the schema portable across SQLite and PostgreSQL and
    let the application assign ids before flush, which simplifies building
    object graphs (e.g. a submission and its attempts) in one transaction.
    """
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Table names are declared explicitly on each model rather than derived, so
    that a rename in Python never silently becomes a schema migration.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:
        """Readable repr showing the primary key."""
        identifier = getattr(self, "id", None)
        return f"<{type(self).__name__} id={identifier!r}>"


class UUIDPrimaryKeyMixin:
    """Adds a string UUID primary key."""

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)


class TimestampMixin:
    """Adds created/updated audit columns maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


JSONDict = dict[str, Any]
JSONList = list[Any]
