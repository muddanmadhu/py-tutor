"""Python reference entries.

The reference is stored in the database rather than served from static files so
it participates in global search, can be cross-linked from lessons, and can
carry per-entry exercises.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferenceEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A documented callable, type, module or third-party API.

    ``key`` is the natural lookup handle a learner would type: ``list.append``,
    ``str.split``, ``requests.get``, ``pathlib.Path``.
    """

    __tablename__ = "reference_entries"
    __table_args__ = (
        Index("ix_reference_entries_module_kind", "module", "kind"),
        Index("ix_reference_entries_key_title", "key", "title"),
    )

    key: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), default="function", nullable=False)
    module: Mapped[str] = mapped_column(String(80), default="builtins", nullable=False)
    signature: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    #: ``[{"name","type","required","default","description"}]``
    parameters: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    returns: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raises: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    #: ``[{"title","code","output","explanation"}]``
    examples: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    real_world_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)
    common_mistakes: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    performance_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    security_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    related_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exercise_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    lesson_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    #: Extra search terms ("timeout", "retry") that should match this entry.
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
