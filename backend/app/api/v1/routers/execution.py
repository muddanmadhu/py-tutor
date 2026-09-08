"""Sandboxed code-execution endpoints (the Code Lab)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import ExecutorKind, get_settings
from app.core.errors import NotFoundError
from app.execution.base import ExecutionResult, build_job
from app.execution.factory import get_executor, get_rate_limiter
from app.models import ExecutionRun, SavedSnippet
from app.models.enums import LearningEventKind
from app.schemas.common import MessageResponse
from app.schemas.learning import (
    ExecuteRequest,
    ExecuteResponse,
    ExecutionHealthResponse,
)
from app.services import analytics, gamification
from app.services.grading import interpret_traceback

router = APIRouter(prefix="/execution", tags=["execution"])


def _reported_result(payload: ExecuteRequest) -> ExecutionResult:
    """Adapt the client's own run into an :class:`ExecutionResult`."""
    reported = payload.execution
    if reported is None:
        return ExecutionResult.infrastructure_failure(
            "No execution result was reported. The in-browser Python engine may "
            "not have finished starting — reload the page and try again.",
            backend="client",
        )
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


@router.post("/run", response_model=ExecuteResponse, summary="Run code in the sandbox")
def run_code(payload: ExecuteRequest, user: CurrentUser, session: DbSession) -> ExecuteResponse:
    """Execute learner code and return its output.

    Where the code actually runs depends on the deployment. With a server-side
    sandbox we run it here. With ``PYFORGE_EXECUTOR=client`` the browser has
    already run it under Pyodide and sends the result, and this endpoint exists
    only to record the run — so history, analytics and streaks stay identical
    either way.
    """
    settings = get_settings()
    get_rate_limiter().check(user.id)

    if settings.client_side_execution:
        result = _reported_result(payload)
    else:
        job = build_job(
            settings,
            files=payload.files,
            mode=payload.mode,
            entrypoint=payload.entrypoint,
            stdin=payload.stdin,
        )
        result = get_executor().run(job)

    session.add(
        ExecutionRun(
            user_id=user.id,
            lesson_slug=payload.lesson_slug,
            exercise_slug=payload.exercise_slug,
            mode=payload.mode.value,
            files=payload.files,
            exit_code=result.exit_code,
            stdout=result.stdout[:20000],
            stderr=result.stderr[:20000],
            timed_out=result.timed_out,
            duration_ms=result.duration_ms,
        )
    )
    analytics.record_event(
        session,
        user,
        LearningEventKind.CODE_EXECUTED,
        subject_type="lesson" if payload.lesson_slug else "code_lab",
        subject_slug=payload.lesson_slug or payload.exercise_slug,
        payload={
            "ok": result.ok,
            "duration_ms": result.duration_ms,
            "timed_out": result.timed_out,
            "files": len(payload.files),
        },
    )
    gamification.touch_streak(user)

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


@router.get("/health", response_model=ExecutionHealthResponse, summary="Engine status")
def execution_health() -> ExecutionHealthResponse:
    """Report which backend is running and whether it can accept work."""
    settings = get_settings()
    executor = get_executor()
    return ExecutionHealthResponse(
        backend=executor.name,
        healthy=executor.healthy(),
        # Client-side runs are isolated too — by the browser's WASM sandbox and
        # same-origin policy, on the learner's own machine rather than ours.
        isolated=settings.executor in {ExecutorKind.DOCKER, ExecutorKind.CLIENT},
        timeout_seconds=settings.exec_timeout_seconds,
        memory_mb=settings.exec_memory_mb,
        max_files=settings.exec_max_files,
    )


@router.get("/snippets", summary="List saved Code Lab workspaces")
def list_snippets(user: CurrentUser, session: DbSession) -> list[dict[str, object]]:
    """Return saved multi-file workspaces, newest first."""
    snippets = session.scalars(
        select(SavedSnippet)
        .where(SavedSnippet.user_id == user.id)
        .order_by(SavedSnippet.updated_at.desc())
    ).all()
    return [
        {
            "id": snippet.id,
            "name": snippet.name,
            "description": snippet.description,
            "entrypoint": snippet.entrypoint,
            "files": snippet.files,
            "updated_at": snippet.updated_at.isoformat(),
        }
        for snippet in snippets
    ]


@router.put("/snippets/{name}", summary="Save a Code Lab workspace")
def save_snippet(
    name: str,
    payload: ExecuteRequest,
    user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    """Create or overwrite a named workspace."""
    settings = get_settings()
    build_job(settings, files=payload.files, entrypoint=payload.entrypoint)  # validate only

    snippet = session.scalar(
        select(SavedSnippet).where(SavedSnippet.user_id == user.id, SavedSnippet.name == name)
    )
    if snippet is None:
        snippet = SavedSnippet(user_id=user.id, name=name)
        session.add(snippet)
    snippet.files = payload.files
    snippet.entrypoint = payload.entrypoint
    session.flush()
    return MessageResponse(message=f"Saved '{name}'.")


@router.delete("/snippets/{name}", summary="Delete a saved workspace")
def delete_snippet(name: str, user: CurrentUser, session: DbSession) -> MessageResponse:
    """Remove a saved workspace."""
    snippet = session.scalar(
        select(SavedSnippet).where(SavedSnippet.user_id == user.id, SavedSnippet.name == name)
    )
    if snippet is None:
        raise NotFoundError("Snippet", name)
    session.delete(snippet)
    return MessageResponse(message=f"Deleted '{name}'.")
