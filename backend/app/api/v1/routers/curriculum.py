"""Curriculum endpoints: courses, modules, lessons and concepts."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.core.errors import NotFoundError
from app.schemas.common import MessageResponse
from app.schemas.learning import (
    ConceptResponse,
    CourseDetail,
    CourseSummary,
    LessonDetail,
    LessonProgressResponse,
    RecordTimeRequest,
    SaveScratchRequest,
)
from app.services.curriculum import CurriculumService
from app.services.progress import ProgressService

router = APIRouter(tags=["curriculum"])


@router.get("/courses", response_model=list[CourseSummary], summary="List courses")
def list_courses(session: DbSession) -> list[CourseSummary]:
    """Every published learning path."""
    return CurriculumService(session).list_courses()


@router.get("/courses/{course_slug}", response_model=CourseDetail, summary="Course detail")
def get_course(course_slug: str, session: DbSession, user: OptionalUser) -> CourseDetail:
    """Return a course with its module and lesson tree, personalised when signed in."""
    return CurriculumService(session).get_course(course_slug, user_id=user.id if user else None)


@router.get("/lessons/{lesson_slug}", response_model=LessonDetail, summary="Lesson detail")
def get_lesson(lesson_slug: str, session: DbSession, user: OptionalUser) -> LessonDetail:
    """Full lesson content, with the learner's progress when signed in."""
    return CurriculumService(session).get_lesson(lesson_slug, user_id=user.id if user else None)


@router.post(
    "/lessons/{lesson_slug}/view",
    response_model=LessonProgressResponse,
    summary="Record a lesson view",
)
def view_lesson(lesson_slug: str, user: CurrentUser, session: DbSession) -> LessonProgressResponse:
    """Mark a lesson as opened and start its progress record."""
    progress = ProgressService(session).view_lesson(user, lesson_slug)
    return LessonProgressResponse.model_validate(progress)


@router.put(
    "/lessons/{lesson_slug}/scratch",
    response_model=LessonProgressResponse,
    summary="Autosave lesson editor state",
)
def save_scratch(
    lesson_slug: str,
    payload: SaveScratchRequest,
    user: CurrentUser,
    session: DbSession,
) -> LessonProgressResponse:
    """Persist the learner's scratch files for a lesson."""
    progress = ProgressService(session).save_scratch(
        user, lesson_slug, payload.files, payload.notes
    )
    return LessonProgressResponse.model_validate(progress)


@router.post(
    "/lessons/{lesson_slug}/time",
    response_model=LessonProgressResponse,
    summary="Report time on task",
)
def record_time(
    lesson_slug: str,
    payload: RecordTimeRequest,
    user: CurrentUser,
    session: DbSession,
) -> LessonProgressResponse:
    """Add elapsed seconds to a lesson's time-on-task."""
    progress = ProgressService(session).record_time(user, lesson_slug, payload.seconds)
    return LessonProgressResponse.model_validate(progress)


@router.post(
    "/lessons/{lesson_slug}/complete",
    response_model=LessonProgressResponse,
    summary="Complete a lesson",
)
def complete_lesson(
    lesson_slug: str, user: CurrentUser, session: DbSession
) -> LessonProgressResponse:
    """Mark a lesson complete, if its exercises have been passed."""
    progress = ProgressService(session).complete_lesson(user, lesson_slug)
    return LessonProgressResponse.model_validate(progress)


@router.get("/concepts", response_model=list[ConceptResponse], summary="List concepts")
def list_concepts(session: DbSession, category: str | None = None) -> list[ConceptResponse]:
    """Every concept in the curriculum, optionally filtered by category."""
    return CurriculumService(session).list_concepts(category=category)


@router.get("/concepts/{concept_slug}", response_model=ConceptResponse, summary="Concept detail")
def get_concept(concept_slug: str, session: DbSession) -> ConceptResponse:
    """One concept and its prerequisites."""
    concept = CurriculumService(session).get_concept(concept_slug)
    if concept is None:
        raise NotFoundError("Concept", concept_slug)
    return concept


@router.get(
    "/concepts/{concept_slug}/lessons",
    response_model=list[str],
    summary="Lessons teaching a concept",
)
def lessons_for_concept(concept_slug: str, session: DbSession) -> list[str]:
    """Slugs of every lesson that teaches this concept."""
    return CurriculumService(session).lessons_for_concept(concept_slug)


@router.get("/health/curriculum", response_model=MessageResponse, include_in_schema=False)
def curriculum_health(session: DbSession) -> MessageResponse:
    """Report how much content is loaded — used by the seed check in CI."""
    counts = CurriculumService(session).content_counts()
    return MessageResponse(
        message=", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
    )
