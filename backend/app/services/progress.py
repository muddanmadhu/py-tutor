"""Progress tracking and the learner dashboard aggregate."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.db.base import utcnow
from app.models import (
    Certification,
    Course,
    Exercise,
    Lesson,
    LessonProgress,
    Module,
    Project,
    ProjectSubmission,
    Submission,
    User,
    UserAchievement,
)
from app.models.enums import LearningEventKind, SubmissionStatus
from app.services import analytics, gamification
from app.services.adaptive import AdaptiveService
from app.services.analytics import AnalyticsService
from app.services.mastery import MasteryService


class ProgressService:
    """Lesson progress, course roll-ups and the dashboard."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mastery = MasteryService(session)
        self._adaptive = AdaptiveService(session)
        self._analytics = AnalyticsService(session)

    # -- lesson progress ----------------------------------------------------

    def view_lesson(self, user: User, lesson_slug: str) -> LessonProgress:
        """Mark a lesson as viewed and return the progress row."""
        lesson = self._get_lesson(lesson_slug)
        progress = self._get_or_create(user.id, lesson)
        progress.view_count += 1
        if progress.first_viewed_at is None:
            progress.first_viewed_at = utcnow()
        if progress.status == "not_started":
            progress.status = "in_progress"
        analytics.record_event(
            self._session,
            user,
            LearningEventKind.LESSON_VIEWED,
            subject_type="lesson",
            subject_slug=lesson.slug,
        )
        gamification.touch_streak(user)
        self._session.flush()
        return progress

    def save_scratch(
        self, user: User, lesson_slug: str, files: dict[str, str], notes: str | None = None
    ) -> LessonProgress:
        """Persist the learner's editor state for a lesson."""
        lesson = self._get_lesson(lesson_slug)
        progress = self._get_or_create(user.id, lesson)
        progress.scratch_files = files
        if notes is not None:
            progress.notes = notes
        self._session.flush()
        return progress

    def record_time(self, user: User, lesson_slug: str, seconds: int) -> LessonProgress:
        """Add time-on-task to a lesson and to the learner's coding total."""
        lesson = self._get_lesson(lesson_slug)
        progress = self._get_or_create(user.id, lesson)
        delta = max(0, min(seconds, 3600))  # ignore implausible client reports
        progress.time_spent_seconds += delta
        user.total_coding_seconds += delta
        self._session.flush()
        return progress

    def complete_lesson(self, user: User, lesson_slug: str) -> LessonProgress:
        """Mark a lesson complete once its exercises are passed.

        A lesson with exercises cannot be completed by pressing *Next*: the
        status only advances when every attached exercise has a passing
        submission. Lessons with no exercises complete on acknowledgement.
        """
        lesson = self._get_lesson(lesson_slug)
        progress = self._get_or_create(user.id, lesson)
        exercise_ids = [exercise.id for exercise in lesson.exercises]
        progress.exercises_total = len(exercise_ids)

        if exercise_ids:
            passed = int(
                self._session.scalar(
                    select(func.count(func.distinct(Submission.exercise_id))).where(
                        Submission.user_id == user.id,
                        Submission.exercise_id.in_(exercise_ids),
                        Submission.status == SubmissionStatus.PASSED.value,
                    )
                )
                or 0
            )
            progress.exercises_completed = passed
            if passed < len(exercise_ids):
                progress.status = "in_progress"
                self._session.flush()
                return progress

        if progress.status != "completed":
            progress.status = "completed"
            progress.completed_at = utcnow()
            user.xp += lesson.xp_reward
            analytics.record_event(
                self._session,
                user,
                LearningEventKind.LESSON_COMPLETED,
                subject_type="lesson",
                subject_slug=lesson.slug,
            )
            gamification.evaluate_achievements(self._session, user)
        self._session.flush()
        return progress

    # -- roll-ups -----------------------------------------------------------

    def course_progress(self, user_id: str, course_slug: str) -> dict[str, Any]:
        """Per-module completion and mastery for one course."""
        course = self._session.scalar(
            select(Course)
            .options(selectinload(Course.modules).selectinload(Module.lessons))
            .where(Course.slug == course_slug)
        )
        if course is None:
            raise NotFoundError("Course", course_slug)

        completed_ids = set(
            self._session.scalars(
                select(LessonProgress.lesson_id).where(
                    LessonProgress.user_id == user_id, LessonProgress.status == "completed"
                )
            ).all()
        )
        started_ids = set(
            self._session.scalars(
                select(LessonProgress.lesson_id).where(
                    LessonProgress.user_id == user_id, LessonProgress.status != "not_started"
                )
            ).all()
        )
        mastery = self._mastery.view_by_slug(user_id)

        modules: list[dict[str, Any]] = []
        total_lessons = total_completed = 0
        for module in course.modules:
            lesson_ids = [lesson.id for lesson in module.lessons]
            completed = sum(1 for lesson_id in lesson_ids if lesson_id in completed_ids)
            concept_slugs = {
                concept.slug for lesson in module.lessons for concept in lesson.concepts
            }
            scores = [mastery[slug].score for slug in concept_slugs if slug in mastery]
            total_lessons += len(lesson_ids)
            total_completed += completed
            modules.append(
                {
                    "slug": module.slug,
                    "title": module.title,
                    "level": module.level,
                    "position": module.position,
                    "lessons_total": len(lesson_ids),
                    "lessons_completed": completed,
                    "lessons_started": sum(1 for i in lesson_ids if i in started_ids),
                    "completion": round(completed / len(lesson_ids), 4) if lesson_ids else 0.0,
                    "mastery": round(sum(scores) / len(concept_slugs), 4) if concept_slugs else 0.0,
                }
            )

        return {
            "course_slug": course.slug,
            "title": course.title,
            "lessons_total": total_lessons,
            "lessons_completed": total_completed,
            "completion": round(total_completed / total_lessons, 4) if total_lessons else 0.0,
            "modules": modules,
        }

    def dashboard(self, user: User) -> dict[str, Any]:
        """Everything the dashboard renders, in one query batch."""
        summary = self._analytics.learner_summary(user.id)
        level = gamification.level_for_xp(user.xp)
        overall = self._mastery.overall_mastery(user.id)

        projects_completed = int(
            self._session.scalar(
                select(func.count(func.distinct(ProjectSubmission.project_id))).where(
                    ProjectSubmission.user_id == user.id, ProjectSubmission.verdict == "passed"
                )
            )
            or 0
        )
        projects_total = int(self._session.scalar(select(func.count()).select_from(Project)) or 0)

        recent = list(
            self._session.execute(
                select(Submission, Exercise)
                .join(Exercise, Exercise.id == Submission.exercise_id)
                .where(Submission.user_id == user.id)
                .order_by(Submission.created_at.desc())
                .limit(5)
            ).all()
        )

        achievements = list(
            self._session.scalars(
                select(UserAchievement)
                .options(selectinload(UserAchievement.achievement))
                .where(UserAchievement.user_id == user.id)
                .order_by(UserAchievement.earned_at.desc())
                .limit(8)
            ).all()
        )

        certifications = list(
            self._session.scalars(
                select(Certification)
                .where(Certification.user_id == user.id)
                .order_by(Certification.awarded_at.desc())
            ).all()
        )

        return {
            "user": {
                "display_name": user.display_name,
                "declared_level": user.declared_level,
                "goal": user.goal,
            },
            "overall_mastery": overall,
            "level": {
                "level": level.level,
                "title": level.title,
                "xp": level.xp,
                "xp_into_level": level.xp_into_level,
                "xp_for_next_level": level.xp_for_next_level,
                "progress": level.progress,
            },
            "streak": {
                "current_days": user.streak_days,
                "longest_days": user.longest_streak_days,
                "last_active_on": user.last_active_on.isoformat() if user.last_active_on else None,
            },
            "counters": {
                **summary,
                "projects_completed": projects_completed,
                "projects_total": projects_total,
                "coding_hours": round(user.total_coding_seconds / 3600, 1),
                "concepts_mastered": sum(
                    1 for view in self._mastery.view_for(user.id) if view.is_mastered
                ),
            },
            "weak_areas": [
                {
                    "concept_slug": view.concept_slug,
                    "concept_name": view.concept_name,
                    "score": view.score,
                    "band": view.band.value,
                    "misconceptions": view.top_misconceptions,
                }
                for view in self._mastery.weak_concepts(user.id)
            ],
            "strong_areas": [
                {
                    "concept_slug": view.concept_slug,
                    "concept_name": view.concept_name,
                    "score": view.score,
                }
                for view in self._mastery.strong_concepts(user.id, limit=3)
            ],
            "recommendations": [r.to_dict() for r in self._adaptive.recommend(user)],
            "recent_activity": [
                {
                    "exercise_slug": exercise.slug,
                    "exercise_title": exercise.title,
                    "status": submission.status,
                    "score": submission.score,
                    "at": submission.created_at.isoformat(),
                }
                for submission, exercise in recent
            ],
            "achievements": [
                {
                    "slug": record.achievement.slug,
                    "name": record.achievement.name,
                    "description": record.achievement.description,
                    "icon": record.achievement.icon,
                    "tier": record.achievement.tier,
                    "earned_at": record.earned_at.isoformat(),
                }
                for record in achievements
            ],
            "certifications": [
                {
                    "level": certification.level,
                    "awarded_at": certification.awarded_at.isoformat(),
                    "code": certification.certificate_code,
                    "overall_mastery": certification.overall_mastery,
                }
                for certification in certifications
            ],
            "activity_series": self._analytics.activity_series(user.id, days=30),
            "repeated_mistakes": self._analytics.repeated_mistakes(user.id),
        }

    # -- internals ----------------------------------------------------------

    def _get_lesson(self, slug: str) -> Lesson:
        lesson = self._session.scalar(
            select(Lesson).options(selectinload(Lesson.exercises)).where(Lesson.slug == slug)
        )
        if lesson is None:
            raise NotFoundError("Lesson", slug)
        return lesson

    def _get_or_create(self, user_id: str, lesson: Lesson) -> LessonProgress:
        progress = self._session.scalar(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson.id
            )
        )
        if progress is None:
            progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson.id,
                exercises_total=len(lesson.exercises),
            )
            self._session.add(progress)
            self._session.flush()
        return progress
