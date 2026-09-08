"""Mastery, progress and the raw learning-event stream."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.curriculum import Concept, Lesson
    from app.models.user import User


class ConceptMastery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-learner, per-concept mastery state.

    ``score`` is the headline 0–1 figure shown as a progress bar. It is *not*
    a completion percentage: it is an exponentially-weighted estimate that
    rewards unaided first-time correctness, discounts hint use, and decays with
    time since last practice. See :mod:`app.services.mastery` for the model.
    """

    __tablename__ = "concept_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="user_id_concept_id"),
        Index("ix_concept_mastery_user_id_score", "user_id", "score"),
    )

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )

    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    #: Confidence in ``score`` (0–1): grows with evidence, shrinks with time.
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_try_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    solutions_viewed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Misconception id → number of times observed.
    misconception_counts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    last_practiced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="concept_mastery")
    concept: Mapped[Concept] = relationship(back_populates="mastery_records")

    @property
    def accuracy(self) -> float:
        """Raw pass rate across all attempts."""
        return self.correct_attempts / self.attempts if self.attempts else 0.0


class LessonProgress(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-learner lesson state: viewed, practised, completed."""

    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="user_id_lesson_id"),
        Index("ix_lesson_progress_user_id_status", "user_id", "status"),
    )

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="not_started", nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exercises_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exercises_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Learner's own scratch code, restored when they return to the lesson.
    scratch_files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    first_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="lesson_progress")
    lesson: Mapped[Lesson] = relationship(back_populates="progress")


class LearningEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only analytics event.

    Deliberately schema-light: aggregates are computed on read. Everything the
    analytics service reports (drop-off points, hardest concepts, average
    attempts) is derived from this table plus submissions.
    """

    __tablename__ = "learning_events"
    __table_args__ = (
        Index("ix_learning_events_user_id_occurred_at", "user_id", "occurred_at"),
        Index("ix_learning_events_kind_occurred_at", "kind", "occurred_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_slug: Mapped[str | None] = mapped_column(String(150), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
