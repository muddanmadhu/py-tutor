"""Project academy models: multi-file builds assessed against a rubric."""

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
from app.models.enums import GuidanceLevel, SkillLevel

if TYPE_CHECKING:
    from app.models.user import User


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A buildable project, from *Calculator* to *Enterprise Automation Platform*.

    ``guidance`` implements the fade-out described in spec §50: the same model
    carries a fully-guided beginner project and a requirements-only capstone;
    only the amount of scaffolding in ``milestones`` and ``starter_files``
    differs.
    """

    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_level_position", "level", "position"),)

    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    tagline: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default=SkillLevel.BEGINNER, nullable=False)
    guidance: Mapped[str] = mapped_column(
        String(24), default=GuidanceLevel.FULLY_GUIDED, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_hours: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    is_capstone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: Business requirement document handed to the learner.
    requirements: Mapped[str] = mapped_column(Text, default="", nullable=False)
    architecture_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    suggested_structure: Mapped[str] = mapped_column(Text, default="", nullable=False)
    #: Ordered build steps; empty for requirements-only projects.
    milestones: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    starter_files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    #: Acceptance tests run against the learner's submission.
    acceptance_tests: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    #: Weighted rubric criteria: ``[{"key","label","weight","description"}]``.
    rubric: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    concept_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    prerequisite_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    submissions: Mapped[list[ProjectSubmission]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )


class ProjectWorkspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A learner's in-progress files for a project (autosaved from the IDE)."""

    __tablename__ = "project_workspaces"
    __table_args__ = (UniqueConstraint("user_id", "project_id", name="user_id_project_id"),)

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    entrypoint: Mapped[str] = mapped_column(String(120), default="main.py", nullable=False)
    completed_milestones: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ProjectSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A submitted project build with its rubric evaluation."""

    __tablename__ = "project_submissions"
    __table_args__ = (Index("ix_project_submissions_user_id_project_id", "user_id", "project_id"),)

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)

    #: Automated acceptance-test outcome.
    tests_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tests_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Per-criterion rubric scores: ``[{"key","score","max","comment"}]``.
    rubric_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    verdict: Mapped[str] = mapped_column(String(24), default="in_review", nullable=False)
    review_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)

    user: Mapped[User] = relationship(back_populates="project_submissions")
    project: Mapped[Project] = relationship(back_populates="submissions")
