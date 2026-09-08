"""Exercises, their hints, graders and challenge variants."""

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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ChallengeKind, ExerciseKind, GraderKind, SkillLevel

if TYPE_CHECKING:
    from app.models.curriculum import Lesson
    from app.models.submission import Submission


class Exercise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A gradeable task attached to a lesson.

    The grader contract lives in ``grader_config`` and is interpreted by
    :mod:`app.services.grading`. Keeping it as data (rather than code per
    exercise) is what makes authoring hundreds of exercises tractable.
    """

    __tablename__ = "exercises"
    __table_args__ = (
        Index("ix_exercises_lesson_id_position", "lesson_id", "position"),
        Index("ix_exercises_kind_level", "kind", "level"),
    )

    lesson_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), default=ExerciseKind.CODE, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default=SkillLevel.BEGINNER, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=25, nullable=False)

    #: Files pre-loaded into the editor: ``{"main.py": "..."}``.
    starter_files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    #: Files merged in at grade time but hidden from the learner (test suites).
    hidden_files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    #: Reference solution, revealed only after a pass or an explicit give-up.
    solution_files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    solution_explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)

    grader: Mapped[str] = mapped_column(String(24), default=GraderKind.PYTEST, nullable=False)
    grader_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    #: Concept slugs this exercise assesses; drives mastery updates.
    concept_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    #: Author-supplied wrong-answer patterns → misconception ids.
    misconception_rules: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )

    is_challenge: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    challenge_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    lesson: Mapped[Lesson | None] = relationship(back_populates="exercises")
    hints: Mapped[list[Hint]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="Hint.level",
        passive_deletes=True,
    )
    submissions: Mapped[list[Submission]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def as_challenge_kind(self) -> ChallengeKind | None:
        """Typed accessor for the challenge category."""
        return ChallengeKind(self.challenge_kind) if self.challenge_kind else None


class Hint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One rung of the progressive hint ladder.

    Level 1 is a conceptual nudge; level 4 is a partial solution. The full
    solution is never a hint — it lives on the exercise and is gated separately.
    """

    __tablename__ = "hints"
    __table_args__ = (UniqueConstraint("exercise_id", "level", name="exercise_id_level"),)

    exercise_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    #: Mastery penalty applied when this rung is revealed (0.0–1.0).
    penalty: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)

    exercise: Mapped[Exercise] = relationship(back_populates="hints")


class QuizQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A multiple-choice item used in concept checks and interview practice."""

    __tablename__ = "quiz_questions"
    __table_args__ = (Index("ix_quiz_questions_category_level", "category", "level"),)

    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="general", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default=SkillLevel.BEGINNER, nullable=False)
    concept_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    #: Interview tracks this question belongs to (e.g. ``["sdet", "backend"]``).
    tracks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
