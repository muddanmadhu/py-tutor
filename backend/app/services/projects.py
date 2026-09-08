"""Project academy: workspaces, acceptance testing and rubric evaluation.

A project submission is graded in two passes:

1. **Automated acceptance tests** run in the sandbox against the learner's
   files. These are objective and pass/fail.
2. **Rubric evaluation** scores the criteria the project declares — architecture,
   error handling, testing, documentation, security — by combining acceptance
   results with the static review engine and structural evidence in the files
   (is there a test suite? a README? a Dockerfile? logging?).

The verdict is deliberately conservative: a project cannot pass on rubric
points alone if the acceptance tests fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationFailure
from app.core.logging import get_logger
from app.execution.base import ExecutionResult, build_job
from app.execution.factory import get_executor, get_rate_limiter
from app.models import Project, ProjectSubmission, ProjectWorkspace, User
from app.models.enums import ExecutionMode, LearningEventKind
from app.services import analytics, gamification
from app.services.code_review import Dimension, ReviewResult, review_files
from app.services.grading import grade_pytest
from app.services.mastery import Evidence, MasteryService

logger = get_logger(__name__)

PASS_THRESHOLD = 0.7
PYTEST_ARGS = ("-v", "--tb=short", "--color=no", "-p", "no:cacheprovider")


@dataclass(slots=True)
class ProjectOutcome:
    """Result of evaluating a project submission."""

    submission: ProjectSubmission
    review: ReviewResult
    execution: ExecutionResult | None
    xp_awarded: int


class ProjectService:
    """Workspaces, submissions and rubric evaluation."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mastery = MasteryService(session)

    # -- workspace ----------------------------------------------------------

    def open_workspace(self, user: User, project_slug: str) -> ProjectWorkspace:
        """Return (creating if needed) the learner's workspace for a project."""
        project = self._get_project(project_slug)
        workspace = self._session.scalar(
            select(ProjectWorkspace).where(
                ProjectWorkspace.user_id == user.id, ProjectWorkspace.project_id == project.id
            )
        )
        if workspace is None:
            workspace = ProjectWorkspace(
                user_id=user.id,
                project_id=project.id,
                files=dict(project.starter_files) or {"main.py": "", "README.md": ""},
            )
            self._session.add(workspace)
            analytics.record_event(
                self._session,
                user,
                LearningEventKind.PROJECT_STARTED,
                subject_type="project",
                subject_slug=project.slug,
            )
            self._session.flush()
        return workspace

    def save_workspace(
        self,
        user: User,
        project_slug: str,
        *,
        files: dict[str, str],
        entrypoint: str | None = None,
        completed_milestones: list[str] | None = None,
        notes: str | None = None,
    ) -> ProjectWorkspace:
        """Autosave the learner's project files."""
        workspace = self.open_workspace(user, project_slug)
        settings = get_settings()
        if len(files) > settings.exec_max_files:
            raise ValidationFailure(
                f"Projects are limited to {settings.exec_max_files} files.",
                details={"submitted": len(files)},
            )
        workspace.files = files
        if entrypoint:
            workspace.entrypoint = entrypoint
        if completed_milestones is not None:
            workspace.completed_milestones = completed_milestones
        if notes is not None:
            workspace.notes = notes
        self._session.flush()
        return workspace

    def run_workspace(self, user: User, project_slug: str) -> ExecutionResult:
        """Run the project's entrypoint in the sandbox."""
        workspace = self.open_workspace(user, project_slug)
        get_rate_limiter().check(user.id)
        job = build_job(
            get_settings(),
            files=workspace.files,
            mode=ExecutionMode.SCRIPT,
            entrypoint=workspace.entrypoint,
        )
        return get_executor().run(job)

    # -- submission ---------------------------------------------------------

    def submit(self, user: User, project_slug: str, files: dict[str, str]) -> ProjectOutcome:
        """Evaluate a project build against its acceptance tests and rubric."""
        project = self._get_project(project_slug)
        get_rate_limiter().check(user.id)

        execution: ExecutionResult | None = None
        tests_passed = tests_total = 0

        if project.acceptance_tests:
            runnable = {**files, **project.acceptance_tests}
            job = build_job(
                get_settings(),
                files=runnable,
                mode=ExecutionMode.PYTEST,
                pytest_args=PYTEST_ARGS,
                timeout_seconds=min(60.0, get_settings().exec_timeout_seconds * 3),
            )
            execution = get_executor().run(job)
            # Reuse the pytest grader's tally parsing.
            stub = _AcceptanceStub()
            graded = grade_pytest(stub, execution)  # type: ignore[arg-type]
            tests_passed = sum(1 for check in graded.checks if check.passed)
            tests_total = len(graded.checks)

        review = review_files(files)
        rubric_scores = self._score_rubric(project, files, review, tests_passed, tests_total)
        overall = _weighted_average(rubric_scores)

        acceptance_ratio = tests_passed / tests_total if tests_total else 1.0
        verdict = (
            "passed" if overall >= PASS_THRESHOLD and acceptance_ratio >= 0.8 else "needs_work"
        )

        attempt_number = 1 + int(
            self._session.scalar(
                select(func.count())
                .select_from(ProjectSubmission)
                .where(
                    ProjectSubmission.user_id == user.id,
                    ProjectSubmission.project_id == project.id,
                )
            )
            or 0
        )

        submission = ProjectSubmission(
            user_id=user.id,
            project_id=project.id,
            attempt_number=attempt_number,
            files=files,
            tests_passed=tests_passed,
            tests_total=tests_total,
            rubric_scores=rubric_scores,
            overall_score=overall,
            verdict=verdict,
            review_markdown=_render_review(
                project, review, rubric_scores, tests_passed, tests_total, verdict
            ),
            stdout=(execution.stdout if execution else "")[:20000],
            stderr=(execution.stderr if execution else "")[:20000],
        )
        self._session.add(submission)
        self._session.flush()

        self._mastery.record(
            user,
            project.concept_slugs,
            Evidence(
                raw_score=overall,
                difficulty=0.75,
                first_attempt=attempt_number == 1,
                hints_used=0,
                solution_viewed=False,
            ),
        )

        xp = 0
        if verdict == "passed" and attempt_number >= 1:
            already = int(
                self._session.scalar(
                    select(func.count())
                    .select_from(ProjectSubmission)
                    .where(
                        ProjectSubmission.user_id == user.id,
                        ProjectSubmission.project_id == project.id,
                        ProjectSubmission.verdict == "passed",
                    )
                )
                or 0
            )
            if already <= 1:
                xp = project.xp_reward
                user.xp += xp

        analytics.record_event(
            self._session,
            user,
            LearningEventKind.PROJECT_SUBMITTED,
            subject_type="project",
            subject_slug=project.slug,
            payload={
                "verdict": verdict,
                "overall_score": overall,
                "tests_passed": tests_passed,
                "tests_total": tests_total,
                "attempt": attempt_number,
            },
        )
        gamification.touch_streak(user)
        gamification.evaluate_achievements(self._session, user)

        return ProjectOutcome(
            submission=submission, review=review, execution=execution, xp_awarded=xp
        )

    def history(self, user_id: str, project_slug: str) -> list[ProjectSubmission]:
        """Past submissions for a project, newest first."""
        project = self._get_project(project_slug)
        return list(
            self._session.scalars(
                select(ProjectSubmission)
                .where(
                    ProjectSubmission.user_id == user_id,
                    ProjectSubmission.project_id == project.id,
                )
                .order_by(ProjectSubmission.created_at.desc())
            ).all()
        )

    # -- rubric -------------------------------------------------------------

    def _score_rubric(
        self,
        project: Project,
        files: dict[str, str],
        review: ReviewResult,
        tests_passed: int,
        tests_total: int,
    ) -> list[dict[str, Any]]:
        """Score each declared rubric criterion from objective evidence."""
        evidence = _gather_evidence(files, review, tests_passed, tests_total)
        scored: list[dict[str, Any]] = []
        for criterion in project.rubric:
            key = str(criterion.get("key", ""))
            weight = float(criterion.get("weight", 1.0))
            score, comment = evidence.get(
                key, (review.overall_score, "Scored from the overall code-quality review.")
            )
            scored.append(
                {
                    "key": key,
                    "label": criterion.get("label", key.replace("_", " ").title()),
                    "weight": weight,
                    "score": round(score, 4),
                    "max": 1.0,
                    "comment": comment,
                }
            )
        return scored

    def _get_project(self, slug: str) -> Project:
        project = self._session.scalar(select(Project).where(Project.slug == slug))
        if project is None:
            raise NotFoundError("Project", slug)
        return project


class _AcceptanceStub:
    """Minimal stand-in so the pytest grader can be reused for acceptance runs."""

    slug = "project-acceptance"
    misconception_rules: list[dict[str, Any]] = []
    grader_config: dict[str, Any] = {}


def _gather_evidence(
    files: dict[str, str],
    review: ReviewResult,
    tests_passed: int,
    tests_total: int,
) -> dict[str, tuple[float, str]]:
    """Turn the file set and review into per-criterion scores."""
    joined = "\n".join(files.values())
    test_files = [name for name in files if "test" in name.lower() and name.endswith(".py")]
    has_readme = any(name.lower().startswith("readme") for name in files)
    has_requirements = any(name in {"requirements.txt", "pyproject.toml"} for name in files)
    has_dockerfile = any(name.lower() == "dockerfile" for name in files)
    package_dirs = {name.split("/")[0] for name in files if "/" in name}
    dimension = review.dimension_scores

    acceptance = tests_passed / tests_total if tests_total else 1.0

    return {
        "correctness": (
            acceptance,
            f"{tests_passed}/{tests_total} acceptance tests passed."
            if tests_total
            else "No acceptance tests are attached to this project.",
        ),
        "architecture": (
            min(1.0, 0.4 + 0.15 * len(package_dirs) + 0.3 * float(len(files) >= 4)),
            f"{len(files)} files across {len(package_dirs) or 1} package(s). "
            "Separate concerns into modules rather than one large file.",
        ),
        "testing": (
            min(1.0, 0.3 * len(test_files) + (0.4 if tests_total and acceptance > 0.8 else 0.0)),
            f"{len(test_files)} test file(s) found."
            if test_files
            else "No test files found. Production code ships with tests.",
        ),
        "error_handling": (
            dimension.get(Dimension.ERROR_HANDLING.value, 1.0),
            "Based on exception-handling findings in the review.",
        ),
        "security": (
            dimension.get(Dimension.SECURITY.value, 1.0),
            "Based on the security scan: injection, secrets and unsafe deserialisation.",
        ),
        "performance": (
            dimension.get(Dimension.PERFORMANCE.value, 1.0),
            "Based on algorithmic and allocation findings.",
        ),
        "readability": (
            dimension.get(Dimension.READABILITY.value, 1.0),
            "Based on naming, docstrings and nesting.",
        ),
        "maintainability": (
            dimension.get(Dimension.MAINTAINABILITY.value, 1.0),
            "Based on function size, parameter counts and coupling.",
        ),
        "logging": (
            1.0 if "logging" in joined or "logger" in joined else 0.2,
            "Uses the logging module."
            if "logging" in joined
            else "No logging found. print() is not observability.",
        ),
        "documentation": (
            (0.5 if has_readme else 0.0) + (0.5 * dimension.get(Dimension.READABILITY.value, 0.0)),
            "README present." if has_readme else "No README. Document how to run and use it.",
        ),
        "deployment": (
            (0.5 if has_dockerfile else 0.0) + (0.5 if has_requirements else 0.0),
            "Dockerfile and dependency manifest present."
            if has_dockerfile and has_requirements
            else "Add a dependency manifest and a Dockerfile so the app can be deployed.",
        ),
        "documentation_quality": (
            dimension.get(Dimension.READABILITY.value, 1.0),
            "Based on docstring coverage.",
        ),
    }


def _weighted_average(scored: list[dict[str, Any]]) -> float:
    total_weight = sum(float(item["weight"]) for item in scored)
    if not total_weight:
        return 0.0
    return round(
        sum(float(item["score"]) * float(item["weight"]) for item in scored) / total_weight, 4
    )


def _render_review(
    project: Project,
    review: ReviewResult,
    rubric_scores: list[dict[str, Any]],
    tests_passed: int,
    tests_total: int,
    verdict: str,
) -> str:
    """Render the engineering review a learner reads after submitting."""
    header = (
        f"# Project review — {project.title}\n\n"
        f"**Verdict:** {'Passed' if verdict == 'passed' else 'Needs work'}  \n"
        f"**Acceptance tests:** {tests_passed}/{tests_total}  \n"
        f"**Overall quality:** {round(review.overall_score * 100)}%\n"
    )

    rubric_table = (
        "\n## Rubric\n\n| Criterion | Score | Notes |\n| --- | --- | --- |\n"
        + "\n".join(
            f"| {item['label']} | {round(float(item['score']) * 100)}% | {item['comment']} |"
            for item in rubric_scores
        )
    )

    if review.strengths:
        strengths = "\n\n## What's working\n\n" + "\n".join(
            f"- {strength}" for strength in review.strengths
        )
    else:
        strengths = ""

    critical = [f for f in review.findings if f.severity.value in {"critical", "major"}]
    if critical:
        issues = "\n\n## Address these first\n\n" + "\n".join(
            f"- **{finding.file}:{finding.line or '?'}** — {finding.message} *{finding.suggestion}*"
            for finding in critical[:12]
        )
    else:
        issues = "\n\n## Address these first\n\nNothing critical or major. Good work."

    return header + rubric_table + strengths + issues + "\n\n" + review.summary
