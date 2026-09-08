"""Progress, mastery, dashboard, achievements and certification endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.models import Achievement, UserAchievement
from app.models.enums import CertificationLevel
from app.schemas.learning import (
    AchievementResponse,
    CertificationStatusResponse,
    MasteryItem,
    MasteryOverview,
    RecommendationResponse,
)
from app.services.adaptive import AdaptiveService
from app.services.certification import CertificationService
from app.services.mastery import MasteryService, MasteryView
from app.services.progress import ProgressService

router = APIRouter(tags=["progress"])


def _to_item(view: MasteryView) -> MasteryItem:
    """Adapt a :class:`MasteryView` dataclass to its response schema."""
    return MasteryItem(
        concept_slug=view.concept_slug,
        concept_name=view.concept_name,
        category=view.category,
        level=view.level,
        score=view.score,
        percent=view.percent,
        confidence=view.confidence,
        band=view.band.value,
        attempts=view.attempts,
        accuracy=view.accuracy,
        hints_used=view.hints_used,
        is_mastered=view.is_mastered,
        last_practiced_at=view.last_practiced_at,
        top_misconceptions=view.top_misconceptions,
    )


@router.get("/dashboard", summary="Learner dashboard")
def dashboard(user: CurrentUser, session: DbSession) -> dict[str, object]:
    """Everything the dashboard renders."""
    return ProgressService(session).dashboard(user)


@router.get("/mastery", response_model=MasteryOverview, summary="Mastery overview")
def mastery(user: CurrentUser, session: DbSession) -> MasteryOverview:
    """Per-concept mastery with weak and strong areas."""
    service = MasteryService(session)
    views = service.view_for(user.id)
    return MasteryOverview(
        overall=service.overall_mastery(user.id),
        concepts=[_to_item(view) for view in views],
        weak_areas=[_to_item(view) for view in service.weak_concepts(user.id)],
        strong_areas=[_to_item(view) for view in service.strong_concepts(user.id)],
        mastered_count=sum(1 for view in views if view.is_mastered),
    )


@router.get("/mastery/readiness", summary="Concept readiness map")
def readiness(user: CurrentUser, session: DbSession) -> list[dict[str, object]]:
    """Which concepts are unlocked, and what is blocking the rest."""
    return AdaptiveService(session).concept_readiness(user.id)


@router.get(
    "/recommendations",
    response_model=list[RecommendationResponse],
    summary="What to study next",
)
def recommendations(user: CurrentUser, session: DbSession) -> list[RecommendationResponse]:
    """Prioritised next steps from the adaptive engine."""
    return [
        RecommendationResponse(**item.to_dict())
        for item in AdaptiveService(session).recommend(user)
    ]


@router.get("/progress/courses/{course_slug}", summary="Course progress")
def course_progress(course_slug: str, user: CurrentUser, session: DbSession) -> dict[str, object]:
    """Per-module completion and mastery for one course."""
    return ProgressService(session).course_progress(user.id, course_slug)


@router.get("/achievements", response_model=list[AchievementResponse], summary="Badges")
def achievements(user: CurrentUser, session: DbSession) -> list[AchievementResponse]:
    """Every badge, marked earned or not."""
    from sqlalchemy import select

    earned = {
        record.achievement_id: record
        for record in session.scalars(
            select(UserAchievement).where(UserAchievement.user_id == user.id)
        ).all()
    }
    definitions = session.scalars(select(Achievement).order_by(Achievement.tier)).all()
    return [
        AchievementResponse(
            slug=definition.slug,
            name=definition.name,
            description=definition.description,
            icon=definition.icon,
            tier=definition.tier,
            xp_reward=definition.xp_reward,
            earned=definition.id in earned,
            earned_at=earned[definition.id].earned_at if definition.id in earned else None,
        )
        for definition in definitions
        if not definition.is_hidden or definition.id in earned
    ]


@router.get(
    "/certifications",
    response_model=list[CertificationStatusResponse],
    summary="Certification progress",
)
def certifications(user: CurrentUser, session: DbSession) -> list[CertificationStatusResponse]:
    """Status of every certification track."""
    return [
        CertificationStatusResponse(**status.to_dict())
        for status in CertificationService(session).status_for(user)
    ]


@router.post(
    "/certifications/{level}/claim",
    response_model=CertificationStatusResponse,
    summary="Claim an earned certification",
)
def claim_certification(
    level: CertificationLevel, user: CurrentUser, session: DbSession
) -> CertificationStatusResponse:
    """Award a certification whose requirements are met."""
    service = CertificationService(session)
    service.claim(user, level)
    status = next(item for item in service.status_for(user) if item.level is level)
    return CertificationStatusResponse(**status.to_dict())
