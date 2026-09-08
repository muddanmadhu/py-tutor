"""Project academy endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.models import Project, ProjectSubmission
from app.schemas.learning import (
    ExecuteResponse,
    ProjectDetail,
    ProjectSubmissionResponse,
    ProjectSubmitRequest,
    ProjectSummary,
    ProjectWorkspaceResponse,
    SaveWorkspaceRequest,
)
from app.services.grading import interpret_traceback
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary], summary="List projects")
def list_projects(
    user: CurrentUser,
    session: DbSession,
    level: str | None = Query(default=None),
) -> list[ProjectSummary]:
    """Return the academy catalogue with the learner's status on each project."""
    query = select(Project).order_by(Project.position, Project.title)
    if level:
        query = query.where(Project.level == level)
    projects = list(session.scalars(query).all())

    best_scores = {
        str(project_id): (float(score or 0.0), str(verdict))
        for project_id, score, verdict in session.execute(
            select(
                ProjectSubmission.project_id,
                func.max(ProjectSubmission.overall_score),
                func.max(ProjectSubmission.verdict),
            )
            .where(ProjectSubmission.user_id == user.id)
            .group_by(ProjectSubmission.project_id)
        ).all()
    }
    passed = set(
        session.scalars(
            select(ProjectSubmission.project_id).where(
                ProjectSubmission.user_id == user.id, ProjectSubmission.verdict == "passed"
            )
        ).all()
    )

    return [
        ProjectSummary(
            slug=project.slug,
            title=project.title,
            tagline=project.tagline,
            level=project.level,
            guidance=project.guidance,
            estimated_hours=project.estimated_hours,
            xp_reward=project.xp_reward,
            is_capstone=project.is_capstone,
            concept_slugs=project.concept_slugs,
            status="passed"
            if project.id in passed
            else "in_progress"
            if project.id in best_scores
            else "not_started",
            best_score=best_scores.get(project.id, (0.0, ""))[0],
        )
        for project in projects
    ]


@router.get("/{project_slug}", response_model=ProjectDetail, summary="Project brief")
def get_project(project_slug: str, user: CurrentUser, session: DbSession) -> ProjectDetail:
    """Return the requirement document, rubric and the learner's workspace."""
    project = session.scalar(select(Project).where(Project.slug == project_slug))
    if project is None:
        raise NotFoundError("Project", project_slug)

    workspace = ProjectService(session).open_workspace(user, project_slug)
    best = float(
        session.scalar(
            select(func.coalesce(func.max(ProjectSubmission.overall_score), 0.0)).where(
                ProjectSubmission.user_id == user.id,
                ProjectSubmission.project_id == project.id,
            )
        )
        or 0.0
    )
    passed = bool(
        session.scalar(
            select(ProjectSubmission.id).where(
                ProjectSubmission.user_id == user.id,
                ProjectSubmission.project_id == project.id,
                ProjectSubmission.verdict == "passed",
            )
        )
    )

    return ProjectDetail(
        slug=project.slug,
        title=project.title,
        tagline=project.tagline,
        level=project.level,
        guidance=project.guidance,
        estimated_hours=project.estimated_hours,
        xp_reward=project.xp_reward,
        is_capstone=project.is_capstone,
        concept_slugs=project.concept_slugs,
        status="passed" if passed else "in_progress" if best else "not_started",
        best_score=best,
        requirements=project.requirements,
        architecture_notes=project.architecture_notes,
        suggested_structure=project.suggested_structure,
        milestones=project.milestones,
        starter_files=project.starter_files,
        rubric=project.rubric,
        prerequisite_slugs=project.prerequisite_slugs,
        workspace=ProjectWorkspaceResponse.model_validate(workspace),
    )


@router.put(
    "/{project_slug}/workspace",
    response_model=ProjectWorkspaceResponse,
    summary="Autosave a project workspace",
)
def save_workspace(
    project_slug: str,
    payload: SaveWorkspaceRequest,
    user: CurrentUser,
    session: DbSession,
) -> ProjectWorkspaceResponse:
    """Persist the learner's project files."""
    workspace = ProjectService(session).save_workspace(
        user,
        project_slug,
        files=payload.files,
        entrypoint=payload.entrypoint,
        completed_milestones=payload.completed_milestones,
        notes=payload.notes,
    )
    return ProjectWorkspaceResponse.model_validate(workspace)


@router.post("/{project_slug}/run", response_model=ExecuteResponse, summary="Run the project")
def run_project(project_slug: str, user: CurrentUser, session: DbSession) -> ExecuteResponse:
    """Execute the project's entrypoint in the sandbox."""
    result = ProjectService(session).run_workspace(user, project_slug)
    _, explanation = interpret_traceback(result.stderr)
    return ExecuteResponse(
        ok=result.ok,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=result.timed_out,
        duration_ms=result.duration_ms,
        stdout_truncated=result.stdout_truncated,
        stderr_truncated=result.stderr_truncated,
        error=result.error,
        error_explanation=explanation or None,
    )


@router.post(
    "/{project_slug}/submit",
    response_model=ProjectSubmissionResponse,
    summary="Submit a project for evaluation",
)
def submit_project(
    project_slug: str,
    payload: ProjectSubmitRequest,
    user: CurrentUser,
    session: DbSession,
) -> ProjectSubmissionResponse:
    """Run acceptance tests, score the rubric and return the engineering review."""
    outcome = ProjectService(session).submit(user, project_slug, payload.files)
    submission = outcome.submission
    return ProjectSubmissionResponse(
        id=submission.id,
        project_slug=project_slug,
        attempt_number=submission.attempt_number,
        verdict=submission.verdict,
        overall_score=submission.overall_score,
        tests_passed=submission.tests_passed,
        tests_total=submission.tests_total,
        rubric_scores=submission.rubric_scores,
        review_markdown=submission.review_markdown,
        stdout=submission.stdout,
        stderr=submission.stderr,
        xp_awarded=outcome.xp_awarded,
        created_at=submission.created_at,
    )


@router.get(
    "/{project_slug}/submissions",
    response_model=list[ProjectSubmissionResponse],
    summary="Project submission history",
)
def project_history(
    project_slug: str, user: CurrentUser, session: DbSession
) -> list[ProjectSubmissionResponse]:
    """Past submissions for this project."""
    return [
        ProjectSubmissionResponse(
            id=submission.id,
            project_slug=project_slug,
            attempt_number=submission.attempt_number,
            verdict=submission.verdict,
            overall_score=submission.overall_score,
            tests_passed=submission.tests_passed,
            tests_total=submission.tests_total,
            rubric_scores=submission.rubric_scores,
            review_markdown=submission.review_markdown,
            stdout=submission.stdout,
            stderr=submission.stderr,
            created_at=submission.created_at,
        )
        for submission in ProjectService(session).history(user.id, project_slug)
    ]
