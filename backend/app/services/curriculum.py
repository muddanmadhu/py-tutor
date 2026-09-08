"""Curriculum read service: assembling course, lesson and concept responses."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models import (
    Concept,
    Course,
    Exercise,
    Lesson,
    LessonProgress,
    Module,
    Project,
    ReferenceEntry,
    Submission,
)
from app.models.enums import SubmissionStatus
from app.schemas.learning import (
    ConceptResponse,
    CourseDetail,
    CourseSummary,
    ExampleBlock,
    ExerciseSummary,
    LessonDetail,
    LessonProgressResponse,
    LessonSummary,
    ModuleSummary,
)


class CurriculumService:
    """Builds curriculum responses, personalised when a learner is known."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- courses ------------------------------------------------------------

    def list_courses(self) -> list[CourseSummary]:
        """Every published course with its counts."""
        courses = self._session.scalars(
            select(Course)
            .options(selectinload(Course.modules).selectinload(Module.lessons))
            .where(Course.is_published.is_(True))
            .order_by(Course.position)
        ).all()
        return [
            CourseSummary(
                slug=course.slug,
                title=course.title,
                subtitle=course.subtitle,
                description=course.description,
                level=course.level,
                estimated_hours=course.estimated_hours,
                outcomes=course.outcomes,
                module_count=len(course.modules),
                lesson_count=sum(len(module.lessons) for module in course.modules),
            )
            for course in courses
        ]

    def get_course(self, slug: str, user_id: str | None = None) -> CourseDetail:
        """One course with its full module/lesson tree."""
        course = self._session.scalar(
            select(Course)
            .options(
                selectinload(Course.modules)
                .selectinload(Module.lessons)
                .selectinload(Lesson.concepts),
                selectinload(Course.modules)
                .selectinload(Module.lessons)
                .selectinload(Lesson.exercises),
            )
            .where(Course.slug == slug)
        )
        if course is None:
            raise NotFoundError("Course", slug)

        statuses = self._lesson_statuses(user_id)
        modules = [
            ModuleSummary(
                slug=module.slug,
                title=module.title,
                summary=module.summary,
                level=module.level,
                position=module.position,
                estimated_minutes=module.estimated_minutes,
                lessons=[self._lesson_summary(lesson, statuses) for lesson in module.lessons],
            )
            for module in course.modules
        ]
        return CourseDetail(
            slug=course.slug,
            title=course.title,
            subtitle=course.subtitle,
            description=course.description,
            level=course.level,
            estimated_hours=course.estimated_hours,
            outcomes=course.outcomes,
            module_count=len(modules),
            lesson_count=sum(len(module.lessons) for module in modules),
            modules=modules,
        )

    # -- lessons ------------------------------------------------------------

    def get_lesson(self, slug: str, user_id: str | None = None) -> LessonDetail:
        """Full lesson content plus navigation and (optional) progress."""
        lesson = self._session.scalar(
            select(Lesson)
            .options(
                selectinload(Lesson.concepts).selectinload(Concept.prerequisites),
                selectinload(Lesson.exercises),
                selectinload(Lesson.module).selectinload(Module.course),
            )
            .where(Lesson.slug == slug)
        )
        if lesson is None:
            raise NotFoundError("Lesson", slug)

        progress: LessonProgressResponse | None = None
        exercise_state: dict[str, tuple[str, float]] = {}
        if user_id:
            record = self._session.scalar(
                select(LessonProgress).where(
                    LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson.id
                )
            )
            if record:
                progress = LessonProgressResponse.model_validate(record)
            exercise_state = self._exercise_states(
                user_id, [exercise.id for exercise in lesson.exercises]
            )

        previous_slug, next_slug = self._neighbours(lesson)

        return LessonDetail(
            slug=lesson.slug,
            title=lesson.title,
            summary=lesson.summary,
            level=lesson.level,
            position=lesson.position,
            estimated_minutes=lesson.estimated_minutes,
            body=lesson.body,
            sections=lesson.sections,
            starter_code=lesson.starter_code,
            examples=[ExampleBlock(**example) for example in lesson.examples],
            visualizations=lesson.visualizations,
            reference_keys=lesson.reference_keys,
            xp_reward=lesson.xp_reward,
            module_slug=lesson.module.slug,
            module_title=lesson.module.title,
            course_slug=lesson.module.course.slug,
            concepts=[self._concept_response(concept) for concept in lesson.concepts],
            exercises=[
                self._exercise_summary(exercise, exercise_state) for exercise in lesson.exercises
            ],
            progress=progress,
            next_lesson_slug=next_slug,
            previous_lesson_slug=previous_slug,
        )

    def _neighbours(self, lesson: Lesson) -> tuple[str | None, str | None]:
        """Previous and next lesson slugs in course order."""
        ordered = list(
            self._session.scalars(
                select(Lesson)
                .join(Module, Module.id == Lesson.module_id)
                .where(Module.course_id == lesson.module.course_id)
                .order_by(Module.position, Lesson.position)
            ).all()
        )
        slugs = [item.slug for item in ordered]
        try:
            index = slugs.index(lesson.slug)
        except ValueError:  # pragma: no cover - lesson is always in its own course
            return None, None
        previous_slug = slugs[index - 1] if index > 0 else None
        next_slug = slugs[index + 1] if index + 1 < len(slugs) else None
        return previous_slug, next_slug

    # -- concepts -----------------------------------------------------------

    def list_concepts(self, category: str | None = None) -> list[ConceptResponse]:
        """Every concept, optionally filtered by category."""
        query = select(Concept).options(selectinload(Concept.prerequisites))
        if category:
            query = query.where(Concept.category == category)
        concepts = self._session.scalars(query.order_by(Concept.level, Concept.slug)).all()
        return [self._concept_response(concept) for concept in concepts]

    def get_concept(self, slug: str) -> ConceptResponse | None:
        """One concept, or ``None`` when it does not exist."""
        concept = self._session.scalar(
            select(Concept).options(selectinload(Concept.prerequisites)).where(Concept.slug == slug)
        )
        return self._concept_response(concept) if concept else None

    def lessons_for_concept(self, slug: str) -> list[str]:
        """Lesson slugs teaching a concept."""
        concept = self._session.scalar(
            select(Concept).options(selectinload(Concept.lessons)).where(Concept.slug == slug)
        )
        if concept is None:
            raise NotFoundError("Concept", slug)
        return [lesson.slug for lesson in concept.lessons]

    # -- diagnostics --------------------------------------------------------

    def content_counts(self) -> dict[str, int]:
        """Row counts for each content table."""
        return {
            "courses": self._count(Course),
            "modules": self._count(Module),
            "lessons": self._count(Lesson),
            "concepts": self._count(Concept),
            "exercises": self._count(Exercise),
            "projects": self._count(Project),
            "reference_entries": self._count(ReferenceEntry),
        }

    def _count(self, model: type) -> int:
        return int(self._session.scalar(select(func.count()).select_from(model)) or 0)

    # -- helpers ------------------------------------------------------------

    def _lesson_statuses(self, user_id: str | None) -> dict[str, str]:
        if not user_id:
            return {}
        rows = self._session.execute(
            select(LessonProgress.lesson_id, LessonProgress.status).where(
                LessonProgress.user_id == user_id
            )
        ).all()
        return {str(lesson_id): str(status) for lesson_id, status in rows}

    def _exercise_states(
        self, user_id: str, exercise_ids: list[str]
    ) -> dict[str, tuple[str, float]]:
        """Best score and status per exercise for one learner."""
        if not exercise_ids:
            return {}
        rows = self._session.execute(
            select(
                Submission.exercise_id,
                func.max(Submission.score),
                func.count(Submission.id),
            )
            .where(Submission.user_id == user_id, Submission.exercise_id.in_(exercise_ids))
            .group_by(Submission.exercise_id)
        ).all()
        passed = set(
            self._session.scalars(
                select(Submission.exercise_id).where(
                    Submission.user_id == user_id,
                    Submission.exercise_id.in_(exercise_ids),
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            ).all()
        )
        state: dict[str, tuple[str, float]] = {}
        for exercise_id, best, attempts in rows:
            key = str(exercise_id)
            status = (
                "passed" if exercise_id in passed else "attempted" if attempts else "not_attempted"
            )
            state[key] = (status, float(best or 0.0))
        return state

    @staticmethod
    def _concept_response(concept: Concept) -> ConceptResponse:
        return ConceptResponse(
            slug=concept.slug,
            name=concept.name,
            description=concept.description,
            level=concept.level,
            category=concept.category,
            difficulty=concept.difficulty,
            prerequisites=[prerequisite.slug for prerequisite in concept.prerequisites],
        )

    @staticmethod
    def _lesson_summary(lesson: Lesson, statuses: dict[str, str]) -> LessonSummary:
        return LessonSummary(
            slug=lesson.slug,
            title=lesson.title,
            summary=lesson.summary,
            level=lesson.level,
            position=lesson.position,
            estimated_minutes=lesson.estimated_minutes,
            concept_slugs=[concept.slug for concept in lesson.concepts],
            exercise_count=len(lesson.exercises),
            status=statuses.get(lesson.id, "not_started"),
        )

    @staticmethod
    def _exercise_summary(
        exercise: Exercise, state: dict[str, tuple[str, float]]
    ) -> ExerciseSummary:
        status, best = state.get(exercise.id, ("not_attempted", 0.0))
        return ExerciseSummary(
            slug=exercise.slug,
            title=exercise.title,
            kind=exercise.kind,
            level=exercise.level,
            difficulty=exercise.difficulty,
            estimated_minutes=exercise.estimated_minutes,
            xp_reward=exercise.xp_reward,
            position=exercise.position,
            is_challenge=exercise.is_challenge,
            challenge_kind=exercise.challenge_kind,
            status=status,
            best_score=best,
        )


def serialise_examples(examples: list[dict[str, Any]]) -> list[ExampleBlock]:
    """Coerce stored example dicts into schema objects."""
    return [ExampleBlock(**example) for example in examples]
