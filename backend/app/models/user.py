"""Identity and account models."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SkillLevel, UserRole

if TYPE_CHECKING:
    from app.models.achievement import Certification, UserAchievement
    from app.models.ai import AIConversation
    from app.models.mastery import ConceptMastery, LessonProgress
    from app.models.project import ProjectSubmission
    from app.models.submission import Submission


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A learner, content author or administrator."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    #: Null for accounts that authenticate through an external identity
    #: provider and therefore have no password of ours to verify.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Firebase Authentication's stable user id, when identity is federated.
    #: Matched on in preference to email, which a learner can change.
    firebase_uid: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    role: Mapped[str] = mapped_column(String(20), default=UserRole.LEARNER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Learning profile --------------------------------------------------
    declared_level: Mapped[str] = mapped_column(
        String(20), default=SkillLevel.BEGINNER, nullable=False
    )
    goal: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active_course_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- Gamification ------------------------------------------------------
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_coding_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # --- Preferences (editor theme, font size, a11y options) ---------------
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Relationships -----------------------------------------------------
    submissions: Mapped[list[Submission]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    lesson_progress: Mapped[list[LessonProgress]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    concept_mastery: Mapped[list[ConceptMastery]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    project_submissions: Mapped[list[ProjectSubmission]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    achievements: Mapped[list[UserAchievement]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    certifications: Mapped[list[Certification]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    conversations: Mapped[list[AIConversation]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_admin(self) -> bool:
        """Whether this account has administrative rights."""
        return self.role == UserRole.ADMIN

    @property
    def can_author(self) -> bool:
        """Whether this account may create or edit curriculum content."""
        return self.role in {UserRole.ADMIN, UserRole.AUTHOR}
