"""Python reference, global search, code review, interview and analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import AuthorUser, CurrentUser, DbSession, PaginationParams
from app.core.errors import NotFoundError
from app.models import QuizQuestion, ReferenceEntry
from app.schemas.learning import (
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizQuestionResponse,
    ReferenceDetail,
    ReferenceSummary,
    ReviewRequest,
    ReviewResponse,
    SearchHitResponse,
    SearchResponse,
)
from app.services.analytics import AnalyticsService
from app.services.code_review import review_files
from app.services.search import SearchService

router = APIRouter(tags=["reference"])


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------


@router.get("/reference", response_model=list[ReferenceSummary], summary="Browse the reference")
def list_reference(
    session: DbSession,
    pagination: PaginationParams,
    module: str | None = Query(default=None, description="Filter by module, e.g. 'pathlib'"),
    kind: str | None = Query(default=None, description="function|method|class|module"),
) -> list[ReferenceSummary]:
    """Return the searchable Python reference index."""
    query = select(ReferenceEntry).order_by(ReferenceEntry.module, ReferenceEntry.key)
    if module:
        query = query.where(ReferenceEntry.module == module)
    if kind:
        query = query.where(ReferenceEntry.kind == kind)
    entries = session.scalars(query.limit(pagination.limit).offset(pagination.offset)).all()
    return [ReferenceSummary.model_validate(entry) for entry in entries]


@router.get("/reference/{key:path}", response_model=ReferenceDetail, summary="Reference entry")
def get_reference(key: str, session: DbSession) -> ReferenceDetail:
    """One reference entry: signature, parameters, examples, pitfalls."""
    entry = session.scalar(select(ReferenceEntry).where(ReferenceEntry.key == key))
    if entry is None:
        raise NotFoundError("Reference entry", key)
    return ReferenceDetail.model_validate(entry)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/search", response_model=SearchResponse, summary="Global search")
def search(
    session: DbSession,
    q: str = Query(min_length=1, max_length=200, description="Search query"),
    kinds: str | None = Query(
        default=None, description="Comma-separated: reference,lesson,concept,exercise,project"
    ),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    """Search lessons, concepts, reference entries, exercises and projects at once."""
    wanted = [kind.strip() for kind in kinds.split(",")] if kinds else None
    hits = SearchService(session).search(q, kinds=wanted, limit=limit)
    return SearchResponse(
        query=q,
        total=len(hits),
        hits=[SearchHitResponse(**hit.to_dict()) for hit in hits],
    )


# ---------------------------------------------------------------------------
# Code review
# ---------------------------------------------------------------------------


@router.post("/code-review", response_model=ReviewResponse, summary="Review code")
def code_review(payload: ReviewRequest, _user: CurrentUser) -> ReviewResponse:
    """Run the deterministic senior-engineer review over the supplied files."""
    result = review_files(payload.files)
    return ReviewResponse(**result.to_dict())


# ---------------------------------------------------------------------------
# Interview preparation
# ---------------------------------------------------------------------------


@router.get(
    "/interview/questions",
    response_model=list[QuizQuestionResponse],
    summary="Interview question bank",
)
def interview_questions(
    session: DbSession,
    track: str | None = Query(default=None, description="e.g. sdet, backend, automation"),
    level: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[QuizQuestionResponse]:
    """Questions for interview practice, without their answers."""
    query = select(QuizQuestion)
    if level:
        query = query.where(QuizQuestion.level == level)
    questions = list(session.scalars(query.limit(200)).all())
    if track:
        questions = [item for item in questions if track in item.tracks]
    return [QuizQuestionResponse.model_validate(item) for item in questions[:limit]]


@router.post(
    "/interview/answer",
    response_model=QuizAnswerResponse,
    summary="Check an interview answer",
)
def answer_question(
    payload: QuizAnswerRequest, _user: CurrentUser, session: DbSession
) -> QuizAnswerResponse:
    """Grade one interview question and explain the answer."""
    question = session.scalar(select(QuizQuestion).where(QuizQuestion.slug == payload.slug))
    if question is None:
        raise NotFoundError("Question", payload.slug)
    return QuizAnswerResponse(
        correct=payload.selected_index == question.correct_index,
        correct_index=question.correct_index,
        explanation=question.explanation,
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics/me", summary="Personal learning analytics")
def my_analytics(user: CurrentUser, session: DbSession) -> dict[str, object]:
    """Activity, accuracy and repeated mistakes for the signed-in learner."""
    service = AnalyticsService(session)
    return {
        "summary": service.learner_summary(user.id),
        "activity_series": service.activity_series(user.id, days=60),
        "repeated_mistakes": service.repeated_mistakes(user.id),
    }


@router.get("/analytics/platform", summary="Curriculum analytics (authors)")
def platform_analytics(_user: AuthorUser, session: DbSession) -> dict[str, object]:
    """Cohort analytics used to improve the curriculum."""
    service = AnalyticsService(session)
    return {
        "summary": service.platform_summary(),
        "hardest_exercises": [stat.__dict__ for stat in service.hardest_exercises()],
        "hardest_concepts": [stat.__dict__ for stat in service.hardest_concepts()],
        "drop_off_points": service.drop_off_points(),
    }
