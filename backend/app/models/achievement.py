"""Gamification: achievements, badges and certification records."""

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
    from app.models.user import User


class Achievement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A badge definition.

    ``criteria`` is data interpreted by :mod:`app.services.gamification`, e.g.
    ``{"type": "exercises_passed", "count": 25}`` or
    ``{"type": "concept_mastered", "concept": "closures", "threshold": 0.8}``.
    """

    __tablename__ = "achievements"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(40), default="award", nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="bronze", nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)


class UserAchievement(UUIDPrimaryKeyMixin, Base):
    """Join record: a learner earned a badge at a point in time."""

    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="user_id_achievement_id"),)

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    achievement_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False
    )
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="achievements")
    achievement: Mapped[Achievement] = relationship()


class Certification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An earned certification.

    Certifications are gated on demonstrated mastery, not lesson completion:
    :mod:`app.services.certification` verifies concept-mastery thresholds and
    required project verdicts before a record is written.
    """

    __tablename__ = "certifications"
    __table_args__ = (
        UniqueConstraint("user_id", "level", name="user_id_level"),
        Index("ix_certifications_user_id_awarded_at", "user_id", "awarded_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(48), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: Snapshot of the evidence that justified the award, for auditability.
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    overall_mastery: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    certificate_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="certifications")
