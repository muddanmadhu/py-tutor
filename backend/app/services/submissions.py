"""Submission orchestration: execute → grade → update mastery → award XP.

This is the transaction script that ties the platform together. It is the only
place that knows the *order* of those steps, which keeps the individual
services independent and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationFailure
from app.core.logging import get_logger
from app.execution.base import ExecutionResult, build_job
from app.execution.factory import get_executor, get_rate_limiter
from app.models import Exercise, Hint, HintReveal, Submission, User
from app.models.enums import (
    ExecutionMode,
    GraderKind,
    LearningEventKind,
    SubmissionStatus,
)
from app.services import analytics, gamification
from app.services.grading import GradeResult, grade
from app.services.mastery import Evidence, MasteryService

logger = get_logger(__name__)

#: Verbose output so the grader can attribute a result to each individual test.
PYTEST_ARGS = ("-v", "--tb=short", "--color=no", "-p", "no:cacheprovider")


@dataclass(slots=True)
class SubmissionOutcome:
    """Everything the API needs to answer a submit request."""

    submission: Submission
    grade_result: GradeResult
    execution: ExecutionResult | None
    xp_awarded: int
    newly_earned_achievements: list[str]
    mastery_deltas: list[dict[str, Any]]


class SubmissionService:
    """Runs and grades exercise submissions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mastery = MasteryService(session)

    # -- public API ---------------------------------------------------------

    def submit(
        self,
        user: User,
        exercise_slug: str,
        *,
        files: dict[str, str],
        selected_index: int | None = None,
        time_spent_seconds: int = 0,
        client_execution: ExecutionResult | None = None,
    ) -> SubmissionOutcome:
        """Grade one attempt at an exercise and record all of its consequences.

        ``client_execution`` is the result of a run the *client* performed, used
        when the deployment has no server-side sandbox. It is trusted input and
        is only honoured when the server genuinely cannot execute code itself;
        otherwise the server runs the code and ignores it, so a client cannot
        opt out of real grading by supplying one.
        """
        from app.core.config import get_settings

        exercise = self._get_exercise(exercise_slug)
        grader = GraderKind(exercise.grader)

        execution: ExecutionResult | None = None
        merged_files = {**exercise.starter_files, **files}

        if grader in {GraderKind.PYTEST, GraderKind.STDOUT_MATCH}:
            get_rate_limiter().check(user.id)
            if get_settings().client_side_execution:
                execution = client_execution or ExecutionResult.infrastructure_failure(
                    "No execution result was reported. The in-browser Python engine "
                    "may not have finished starting — reload the page and try again."
                )
            else:
                execution = self._execute_for_grading(exercise, merged_files, grader)

        result = grade(
            exercise,
            files=merged_files,
            result=execution,
            selected_index=selected_index,
        )

        attempt_number = self._next_attempt_number(user.id, exercise.id)
        hints_used = self._hints_revealed(user.id, exercise.id)
        solution_viewed = self._solution_was_viewed(user.id, exercise.id)

        submission = Submission(
            user_id=user.id,
            exercise_id=exercise.id,
            attempt_number=attempt_number,
            files=files,
            status=result.status.value,
            score=result.score,
            checks=[check.to_dict() for check in result.checks],
            feedback=result.feedback,
            stdout=(execution.stdout if execution else "")[:20000],
            stderr=(execution.stderr if execution else "")[:20000],
            duration_ms=execution.duration_ms if execution else 0,
            time_spent_seconds=max(0, time_spent_seconds),
            hints_used=hints_used,
            solution_viewed=solution_viewed,
            misconceptions=result.misconceptions,
        )
        self._session.add(submission)
        self._session.flush()

        mastery_before = self._mastery.view_by_slug(user.id)
        self._mastery.record(
            user,
            exercise.concept_slugs,
            Evidence(
                raw_score=result.score,
                difficulty=exercise.difficulty,
                first_attempt=attempt_number == 1,
                hints_used=hints_used,
                solution_viewed=solution_viewed,
                time_spent_seconds=time_spent_seconds,
                expected_seconds=exercise.estimated_minutes * 60,
            ),
            misconceptions=result.misconceptions,
        )
        mastery_after = self._mastery.view_by_slug(user.id)

        xp = self._award_xp(user, exercise, result, attempt_number, hints_used, solution_viewed)
        earned = gamification.evaluate_achievements(self._session, user)

        analytics.record_event(
            self._session,
            user,
            LearningEventKind.SUBMISSION_GRADED,
            subject_type="exercise",
            subject_slug=exercise.slug,
            payload={
                "status": result.status.value,
                "score": result.score,
                "attempt": attempt_number,
                "hints_used": hints_used,
                "duration_ms": submission.duration_ms,
                "misconceptions": result.misconceptions,
            },
        )
        gamification.touch_streak(user)
        user.total_coding_seconds += max(0, time_spent_seconds)

        return SubmissionOutcome(
            submission=submission,
            grade_result=result,
            execution=execution,
            xp_awarded=xp,
            newly_earned_achievements=earned,
            mastery_deltas=self._deltas(exercise.concept_slugs, mastery_before, mastery_after),
        )

    def reveal_hint(self, user: User, exercise_slug: str, level: int) -> Hint:
        """Unlock the next hint rung.

        Hints must be taken in order: a learner cannot jump to rung 4 to get the
        near-solution while paying only one rung of penalty.
        """
        exercise = self._get_exercise(exercise_slug)
        already = self._hints_revealed(user.id, exercise.id)
        if level > already + 1:
            raise ValidationFailure(
                "Hints unlock one at a time — take the previous hint first.",
                details={"next_available_level": already + 1},
            )

        hint = self._session.scalar(
            select(Hint).where(Hint.exercise_id == exercise.id, Hint.level == level)
        )
        if hint is None:
            raise NotFoundError("Hint", f"{exercise_slug}#{level}")

        if level > already:
            self._session.add(HintReveal(user_id=user.id, exercise_id=exercise.id, level=level))
            # Explicit flush: the session runs with autoflush disabled, so
            # without this the very next `_hints_revealed` read in the same
            # transaction still sees zero and refuses the following rung.
            self._session.flush()
            analytics.record_event(
                self._session,
                user,
                LearningEventKind.HINT_REVEALED,
                subject_type="exercise",
                subject_slug=exercise.slug,
                payload={"level": level},
            )
        return hint

    def reveal_solution(self, user: User, exercise_slug: str) -> Exercise:
        """Unlock the reference solution.

        Permitted only after a genuine effort: three attempts, or every hint
        consumed, or an already-passing submission. The point is to make giving
        up a deliberate act rather than a reflex.
        """
        exercise = self._get_exercise(exercise_slug)
        attempts = self._attempt_count(user.id, exercise.id)
        hints_available = len(exercise.hints)
        hints_taken = self._hints_revealed(user.id, exercise.id)
        has_passed = self._has_passed(user.id, exercise.id)

        if not (
            has_passed or attempts >= 3 or (hints_available and hints_taken >= hints_available)
        ):
            raise ValidationFailure(
                "The solution unlocks after three attempts or once you've used every hint. "
                "Struggling productively is where the learning happens — try the next hint.",
                details={
                    "attempts": attempts,
                    "attempts_required": 3,
                    "hints_taken": hints_taken,
                    "hints_available": hints_available,
                },
            )

        self._session.add(
            HintReveal(
                user_id=user.id,
                exercise_id=exercise.id,
                level=99,
                source="solution",
            )
        )
        self._session.flush()  # see reveal_hint: autoflush is off
        analytics.record_event(
            self._session,
            user,
            LearningEventKind.SOLUTION_VIEWED,
            subject_type="exercise",
            subject_slug=exercise.slug,
            payload={"attempts": attempts},
        )
        return exercise

    def history(self, user_id: str, exercise_slug: str, limit: int = 20) -> list[Submission]:
        """Recent attempts at one exercise, newest first."""
        exercise = self._get_exercise(exercise_slug)
        return list(
            self._session.scalars(
                select(Submission)
                .where(Submission.user_id == user_id, Submission.exercise_id == exercise.id)
                .order_by(Submission.created_at.desc())
                .limit(limit)
            ).all()
        )

    # -- internals ----------------------------------------------------------

    def _execute_for_grading(
        self, exercise: Exercise, files: dict[str, str], grader: GraderKind
    ) -> ExecutionResult:
        """Merge hidden test files and run the sandbox in the right mode."""
        from app.core.config import get_settings

        settings = get_settings()
        if grader is GraderKind.PYTEST:
            runnable = {**files, **exercise.hidden_files}
            job = build_job(
                settings,
                files=runnable,
                mode=ExecutionMode.PYTEST,
                pytest_args=PYTEST_ARGS,
                timeout_seconds=float(exercise.grader_config.get("timeout_seconds", 0)) or None,
            )
        else:
            entrypoint = str(exercise.grader_config.get("entrypoint", "main.py"))
            job = build_job(
                settings,
                files=files,
                mode=ExecutionMode.SCRIPT,
                entrypoint=entrypoint,
                stdin=str(exercise.grader_config.get("stdin", "")),
                timeout_seconds=float(exercise.grader_config.get("timeout_seconds", 0)) or None,
            )
        return get_executor().run(job)

    def _get_exercise(self, slug: str) -> Exercise:
        exercise = self._session.scalar(select(Exercise).where(Exercise.slug == slug))
        if exercise is None:
            raise NotFoundError("Exercise", slug)
        return exercise

    def _next_attempt_number(self, user_id: str, exercise_id: str) -> int:
        return self._attempt_count(user_id, exercise_id) + 1

    def _attempt_count(self, user_id: str, exercise_id: str) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(Submission)
                .where(Submission.user_id == user_id, Submission.exercise_id == exercise_id)
            )
            or 0
        )

    def _hints_revealed(self, user_id: str, exercise_id: str) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(HintReveal)
                .where(
                    HintReveal.user_id == user_id,
                    HintReveal.exercise_id == exercise_id,
                    HintReveal.source == "authored",
                )
            )
            or 0
        )

    def _solution_was_viewed(self, user_id: str, exercise_id: str) -> bool:
        return bool(
            self._session.scalar(
                select(HintReveal.id).where(
                    HintReveal.user_id == user_id,
                    HintReveal.exercise_id == exercise_id,
                    HintReveal.source == "solution",
                )
            )
        )

    def _has_passed(self, user_id: str, exercise_id: str) -> bool:
        return bool(
            self._session.scalar(
                select(Submission.id).where(
                    Submission.user_id == user_id,
                    Submission.exercise_id == exercise_id,
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            )
        )

    def _award_xp(
        self,
        user: User,
        exercise: Exercise,
        result: GradeResult,
        attempt_number: int,
        hints_used: int,
        solution_viewed: bool,
    ) -> int:
        """Grant XP once per exercise, discounted by the help that was used."""
        if not result.passed:
            return 0
        already_passed = (
            self._session.scalar(
                select(func.count())
                .select_from(Submission)
                .where(
                    Submission.user_id == user.id,
                    Submission.exercise_id == exercise.id,
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            )
            or 0
        )
        if already_passed > 1:  # this attempt is already counted
            return 0

        xp = float(exercise.xp_reward)
        if solution_viewed:
            xp *= 0.3
        elif hints_used:
            xp *= max(0.4, 1.0 - 0.15 * hints_used)
        if attempt_number == 1 and not hints_used and not solution_viewed:
            xp *= 1.25  # unaided first-time pass
        awarded = int(round(xp))
        user.xp += awarded
        return awarded

    @staticmethod
    def _deltas(
        concept_slugs: list[str],
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> list[dict[str, Any]]:
        deltas: list[dict[str, Any]] = []
        for slug in concept_slugs:
            new = after.get(slug)
            if new is None:
                continue
            old_score = before[slug].score if slug in before else 0.0
            deltas.append(
                {
                    "concept_slug": slug,
                    "concept_name": new.concept_name,
                    "previous": round(old_score, 4),
                    "current": new.score,
                    "delta": round(new.score - old_score, 4),
                    "band": new.band.value,
                }
            )
        return deltas
