"""Gamification: XP levels, streaks and achievement evaluation.

Gamification is deliberately downstream of assessment. Nothing here can award
mastery or unlock a certification; it only reflects work that the mastery and
grading engines have already validated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import (
    Achievement,
    ConceptMastery,
    LessonProgress,
    ProjectSubmission,
    Submission,
    User,
    UserAchievement,
)
from app.models.enums import SubmissionStatus

#: XP required to reach each level. Growth is super-linear but never punishing.
_LEVEL_STEP = 250


@dataclass(frozen=True, slots=True)
class LevelInfo:
    """Where a learner sits on the XP ladder."""

    level: int
    title: str
    xp: int
    xp_into_level: int
    xp_for_next_level: int

    @property
    def progress(self) -> float:
        """Fraction of the way to the next level."""
        return (
            round(self.xp_into_level / self.xp_for_next_level, 4) if self.xp_for_next_level else 1.0
        )


_LEVEL_TITLES = [
    "Newcomer",
    "Scripter",
    "Programmer",
    "Developer",
    "Practitioner",
    "Engineer",
    "Senior Engineer",
    "Architect",
    "Principal",
    "Master",
]


def level_for_xp(xp: int) -> LevelInfo:
    """Convert an XP total into a level, title and progress bar."""
    level = 1
    remaining = max(0, xp)
    step = _LEVEL_STEP
    while remaining >= step:
        remaining -= step
        level += 1
        step = int(step * 1.15)
    title = _LEVEL_TITLES[min(level - 1, len(_LEVEL_TITLES) - 1)]
    return LevelInfo(
        level=level,
        title=title,
        xp=xp,
        xp_into_level=remaining,
        xp_for_next_level=step,
    )


def touch_streak(user: User, today: date | None = None) -> int:
    """Update the learner's daily streak. Returns the current streak length."""
    today = today or utcnow().date()
    last = user.last_active_on
    if last == today:
        return user.streak_days
    if last == today - timedelta(days=1):
        user.streak_days += 1
    else:
        user.streak_days = 1
    user.last_active_on = today
    user.longest_streak_days = max(user.longest_streak_days, user.streak_days)
    return user.streak_days


def evaluate_achievements(session: Session, user: User) -> list[str]:
    """Award any newly-earned achievements. Returns the slugs granted."""
    earned_ids = set(
        session.scalars(
            select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id)
        ).all()
    )
    candidates = session.scalars(select(Achievement)).all()
    newly_earned: list[str] = []

    for achievement in candidates:
        if achievement.id in earned_ids:
            continue
        if not _criteria_met(session, user, achievement.criteria):
            continue
        session.add(
            UserAchievement(user_id=user.id, achievement_id=achievement.id, earned_at=utcnow())
        )
        user.xp += achievement.xp_reward
        newly_earned.append(achievement.slug)

    if newly_earned:
        session.flush()
    return newly_earned


def _criteria_met(session: Session, user: User, criteria: dict[str, Any]) -> bool:
    """Interpret one achievement criterion."""
    kind = str(criteria.get("type", ""))

    if kind == "exercises_passed":
        needed = int(criteria.get("count", 1))
        return _distinct_passed_exercises(session, user.id) >= needed

    if kind == "lessons_completed":
        needed = int(criteria.get("count", 1))
        done = session.scalar(
            select(func.count())
            .select_from(LessonProgress)
            .where(LessonProgress.user_id == user.id, LessonProgress.status == "completed")
        )
        return int(done or 0) >= needed

    if kind == "concepts_mastered":
        needed = int(criteria.get("count", 1))
        mastered = session.scalar(
            select(func.count())
            .select_from(ConceptMastery)
            .where(ConceptMastery.user_id == user.id, ConceptMastery.mastered_at.is_not(None))
        )
        return int(mastered or 0) >= needed

    if kind == "projects_completed":
        needed = int(criteria.get("count", 1))
        done = session.scalar(
            select(func.count(func.distinct(ProjectSubmission.project_id))).where(
                ProjectSubmission.user_id == user.id, ProjectSubmission.verdict == "passed"
            )
        )
        return int(done or 0) >= needed

    if kind == "streak_days":
        return user.streak_days >= int(criteria.get("count", 1))

    if kind == "unaided_passes":
        needed = int(criteria.get("count", 1))
        unaided = session.scalar(
            select(func.count())
            .select_from(Submission)
            .where(
                Submission.user_id == user.id,
                Submission.status == SubmissionStatus.PASSED.value,
                Submission.attempt_number == 1,
                Submission.hints_used == 0,
                Submission.solution_viewed.is_(False),
            )
        )
        return int(unaided or 0) >= needed

    if kind == "debug_fixes":
        needed = int(criteria.get("count", 1))
        from app.models import Exercise
        from app.models.enums import ExerciseKind

        fixed = session.scalar(
            select(func.count(func.distinct(Submission.exercise_id)))
            .join(Exercise, Exercise.id == Submission.exercise_id)
            .where(
                Submission.user_id == user.id,
                Submission.status == SubmissionStatus.PASSED.value,
                Exercise.kind == ExerciseKind.DEBUG.value,
            )
        )
        return int(fixed or 0) >= needed

    return False


def _distinct_passed_exercises(session: Session, user_id: str) -> int:
    return int(
        session.scalar(
            select(func.count(func.distinct(Submission.exercise_id))).where(
                Submission.user_id == user_id,
                Submission.status == SubmissionStatus.PASSED.value,
            )
        )
        or 0
    )
