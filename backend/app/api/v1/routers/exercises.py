"""Exercise, hint, solution and submission endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, PaginationParams
from app.core.errors import NotFoundError, ValidationFailure
from app.execution.base import ExecutionResult
from app.models.enums import GraderKind
from app.schemas.learning import (
    ChallengeSummary,
    ClientExecutionResult,
    ExerciseDetail,
    HintResponse,
    RemediationResponse,
    SolutionResponse,
    SubmissionHistoryItem,
    SubmissionResponse,
    SubmitRequest,
)
from app.services.adaptive import AdaptiveService
from app.services.exercises import ExerciseService
from app.services.submissions import SubmissionService

router = APIRouter(tags=["exercises"])


def _to_execution_result(reported: ClientExecutionResult | None) -> ExecutionResult | None:
    """Adapt a client-reported run into the shape the graders consume."""
    if reported is None:
        return None
    return ExecutionResult(
        ok=reported.exit_code == 0,
        exit_code=reported.exit_code,
        stdout=reported.stdout,
        stderr=reported.stderr,
        timed_out=reported.timed_out,
        duration_ms=reported.duration_ms,
        stdout_truncated=reported.stdout_truncated,
        stderr_truncated=reported.stderr_truncated,
        meta={"backend": "client"},
    )


@router.get(
    "/exercises/{exercise_slug}",
    response_model=ExerciseDetail,
    summary="Exercise detail",
)
def get_exercise(exercise_slug: str, user: CurrentUser, session: DbSession) -> ExerciseDetail:
    """Everything needed to attempt an exercise (never the hidden tests)."""
    return ExerciseService(session).detail(user, exercise_slug)


@router.post(
    "/exercises/{exercise_slug}/submit",
    response_model=SubmissionResponse,
    summary="Submit an attempt",
)
def submit(
    exercise_slug: str,
    payload: SubmitRequest,
    user: CurrentUser,
    session: DbSession,
) -> SubmissionResponse:
    """Grade one attempt and return the verdict with mastery movement."""
    outcome = SubmissionService(session).submit(
        user,
        exercise_slug,
        files=payload.files,
        selected_index=payload.selected_index,
        time_spent_seconds=payload.time_spent_seconds,
        client_execution=_to_execution_result(payload.execution),
    )
    submission = outcome.submission
    return SubmissionResponse(
        id=submission.id,
        exercise_slug=exercise_slug,
        attempt_number=submission.attempt_number,
        status=submission.status,
        score=submission.score,
        checks=submission.checks,
        feedback=submission.feedback,
        stdout=submission.stdout,
        stderr=submission.stderr,
        duration_ms=submission.duration_ms,
        hints_used=submission.hints_used,
        xp_awarded=outcome.xp_awarded,
        mastery_deltas=outcome.mastery_deltas,
        newly_earned_achievements=outcome.newly_earned_achievements,
        created_at=submission.created_at,
    )


@router.get(
    "/exercises/{exercise_slug}/submissions",
    response_model=list[SubmissionHistoryItem],
    summary="Attempt history",
)
def submission_history(
    exercise_slug: str,
    user: CurrentUser,
    session: DbSession,
    pagination: PaginationParams,
) -> list[SubmissionHistoryItem]:
    """Past attempts at this exercise, newest first."""
    submissions = SubmissionService(session).history(user.id, exercise_slug, limit=pagination.limit)
    return [SubmissionHistoryItem.model_validate(item) for item in submissions]


@router.post(
    "/exercises/{exercise_slug}/hints/{level}",
    response_model=HintResponse,
    summary="Unlock a hint",
)
def reveal_hint(
    exercise_slug: str, level: int, user: CurrentUser, session: DbSession
) -> HintResponse:
    """Unlock the next rung of the hint ladder."""
    if level < 1:
        raise ValidationFailure("Hint levels start at 1.")
    service = SubmissionService(session)
    hint = service.reveal_hint(user, exercise_slug, level)
    total = len(hint.exercise.hints)
    return HintResponse(
        level=hint.level, text=hint.text, penalty=hint.penalty, is_last=hint.level >= total
    )


@router.post(
    "/exercises/{exercise_slug}/solution",
    response_model=SolutionResponse,
    summary="Reveal the reference solution",
)
def reveal_solution(exercise_slug: str, user: CurrentUser, session: DbSession) -> SolutionResponse:
    """Unlock the solution, once enough effort has been demonstrated."""
    exercise = SubmissionService(session).reveal_solution(user, exercise_slug)
    return SolutionResponse(
        files=exercise.solution_files, explanation=exercise.solution_explanation
    )


@router.get(
    "/exercises/{exercise_slug}/remediation",
    response_model=RemediationResponse | None,
    summary="Adaptive help when stuck",
)
def remediation(
    exercise_slug: str, user: CurrentUser, session: DbSession
) -> RemediationResponse | None:
    """Return an adaptive remediation plan, or null when not needed yet."""
    plan = AdaptiveService(session).remediation_plan(user, exercise_slug)
    return RemediationResponse(**plan.to_dict()) if plan else None


@router.get("/challenges", response_model=list[ChallengeSummary], summary="List challenges")
def list_challenges(
    user: CurrentUser,
    session: DbSession,
    kind: str | None = Query(default=None, description="quick|coding|debugging|algorithm|…"),
    level: str | None = Query(default=None),
) -> list[ChallengeSummary]:
    """Return timed and open-ended challenges."""
    return ExerciseService(session).list_challenges(user, kind=kind, level=level)


@router.get(
    "/exercises",
    response_model=list[ChallengeSummary],
    summary="Search the exercise catalogue",
)
def list_exercises(
    user: CurrentUser,
    session: DbSession,
    pagination: PaginationParams,
    concept: str | None = Query(default=None, description="Filter by concept slug"),
    kind: str | None = Query(default=None),
    level: str | None = Query(default=None),
) -> list[ChallengeSummary]:
    """Browse exercises by concept, kind or level."""
    return ExerciseService(session).search(
        user,
        concept=concept,
        kind=kind,
        level=level,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get(
    "/exercises/{exercise_slug}/options",
    response_model=list[str],
    summary="Multiple-choice options",
)
def exercise_options(exercise_slug: str, session: DbSession) -> list[str]:
    """Options for a multiple-choice exercise."""
    exercise = ExerciseService(session).get(exercise_slug)
    if GraderKind(exercise.grader) is not GraderKind.MULTIPLE_CHOICE:
        raise NotFoundError("Options", exercise_slug)
    return list(exercise.grader_config.get("options", []))
