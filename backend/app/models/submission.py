"""Submissions, hint reveals and raw execution records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SubmissionStatus

if TYPE_CHECKING:
    from app.models.exercise import Exercise
    from app.models.user import User


class Submission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One graded attempt at an exercise.

    Every attempt is kept, never overwritten: the mastery engine, the analytics
    layer and the adaptive engine all reason over the *sequence* of attempts,
    not just the latest one.
    """

    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_user_id_exercise_id", "user_id", "exercise_id"),
        Index("ix_submissions_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )

    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=SubmissionStatus.FAILED, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    #: Per-check breakdown from the grader, rendered as a checklist in the UI.
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Wall-clock seconds the learner spent before submitting, reported by the client.
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    solution_viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: Misconception ids inferred by the grader / review engine.
    misconceptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    #: Cached code-review result, when one was requested for this submission.
    review: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    user: Mapped[User] = relationship(back_populates="submissions")
    exercise: Mapped[Exercise] = relationship(back_populates="submissions")

    @property
    def passed(self) -> bool:
        """Whether this attempt fully satisfied the grader."""
        return self.status == SubmissionStatus.PASSED


class HintReveal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Records that a learner unlocked a specific hint rung.

    Persisted so that (a) mastery can be discounted, (b) a learner cannot
    re-lock a hint to dodge the penalty, and (c) analytics can show which
    exercises need better teaching upstream.
    """

    __tablename__ = "hint_reveals"
    __table_args__ = (
        Index("ix_hint_reveals_user_id_exercise_id", "user_id", "exercise_id", unique=False),
    )

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="authored", nullable=False)


class ExecutionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An ad-hoc sandbox run from the Code Lab or a lesson's editor.

    Kept separately from submissions: running code to explore is the core
    activity of the platform and is a signal in its own right (coding time,
    error patterns), but it is not an assessment.
    """

    __tablename__ = "execution_runs"
    __table_args__ = (Index("ix_execution_runs_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lesson_slug: Mapped[str | None] = mapped_column(String(150), nullable=True)
    exercise_slug: Mapped[str | None] = mapped_column(String(150), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="script", nullable=False)
    files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    exit_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SavedSnippet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A learner-saved Code Lab workspace (multi-file, named, reloadable)."""

    __tablename__ = "saved_snippets"
    __table_args__ = (Index("ix_saved_snippets_user_id_name", "user_id", "name"),)

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    entrypoint: Mapped[str] = mapped_column(String(120), default="main.py", nullable=False)
