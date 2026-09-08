"""Curriculum structure: Course → Module → Lesson, plus the Concept graph.

Concepts are deliberately *not* nested inside lessons. A concept such as
"closures" is taught in one lesson, reinforced in three others and assessed in
a project; mastery is tracked per concept, so concepts are first-class and are
linked to lessons and exercises many-to-many.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SkillLevel

if TYPE_CHECKING:
    from app.models.exercise import Exercise
    from app.models.mastery import ConceptMastery, LessonProgress

#: Lessons teach concepts; concepts are taught by many lessons.
lesson_concepts = Table(
    "lesson_concepts",
    Base.metadata,
    Column("lesson_id", String(32), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "concept_id", String(32), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("is_primary", Boolean, default=False, nullable=False),
)

#: Concept prerequisite edges — the directed graph the adaptive engine walks.
concept_prerequisites = Table(
    "concept_prerequisites",
    Base.metadata,
    Column(
        "concept_id", String(32), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "prerequisite_id",
        String(32),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A learning path, e.g. *Python Engineering Mastery*."""

    __tablename__ = "courses"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default=SkillLevel.BEGINNER, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    outcomes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    estimated_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    modules: Mapped[list[Module]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.position",
        passive_deletes=True,
    )


class Module(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A themed group of lessons within a course."""

    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("course_id", "slug", name="course_id_slug"),
        Index("ix_modules_course_id_position", "course_id", "position"),
    )

    course_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default=SkillLevel.BEGINNER, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    course: Mapped[Course] = relationship(back_populates="modules")
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.position",
        passive_deletes=True,
    )


class Lesson(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single unit of instruction.

    ``body`` holds the authored markdown. ``sections`` holds the structured
    parts the UI renders as distinct panels — examples, common mistakes,
    real-world usage, alternatives, performance and security notes — which is
    how the content-quality checklist (spec §49) is enforced mechanically
    rather than by convention.
    """

    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("module_id", "slug", name="module_id_slug"),
        Index("ix_lessons_module_id_position", "module_id", "position"),
    )

    module_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(150), index=True, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default=SkillLevel.BEGINNER, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sections: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, default="", nullable=False)
    examples: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    visualizations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    reference_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    module: Mapped[Module] = relationship(back_populates="lessons")
    concepts: Mapped[list[Concept]] = relationship(
        secondary=lesson_concepts, back_populates="lessons"
    )
    exercises: Mapped[list[Exercise]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="Exercise.position",
        passive_deletes=True,
    )
    progress: Mapped[list[LessonProgress]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", passive_deletes=True
    )


class Concept(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An atomic, masterable idea (e.g. ``list-slicing``, ``closures``).

    ``difficulty`` and ``weight`` feed the mastery calculation: harder concepts
    move a score more slowly, and heavier concepts dominate the roll-up to a
    module- or course-level mastery figure.
    """

    __tablename__ = "concepts"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default=SkillLevel.BEGINNER, nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="core", nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    common_misconceptions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )

    lessons: Mapped[list[Lesson]] = relationship(
        secondary=lesson_concepts, back_populates="concepts"
    )
    #: Concepts that must be understood first. This is the writable side; the
    #: seeder assigns it, and the adaptive engine reads it.
    prerequisites: Mapped[list[Concept]] = relationship(
        secondary=concept_prerequisites,
        primaryjoin=lambda: Concept.id == concept_prerequisites.c.concept_id,
        secondaryjoin=lambda: Concept.id == concept_prerequisites.c.prerequisite_id,
    )
    #: The same edge read the other way: concepts this one unlocks. Read-only,
    #: so there is exactly one place the graph can be modified.
    dependents: Mapped[list[Concept]] = relationship(
        secondary=concept_prerequisites,
        primaryjoin=lambda: Concept.id == concept_prerequisites.c.prerequisite_id,
        secondaryjoin=lambda: Concept.id == concept_prerequisites.c.concept_id,
        viewonly=True,
    )
    mastery_records: Mapped[list[ConceptMastery]] = relationship(
        back_populates="concept", cascade="all, delete-orphan", passive_deletes=True
    )
