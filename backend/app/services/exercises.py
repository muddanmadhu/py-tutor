"""Exercise read service."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models import Exercise, HintReveal, Submission, User
from app.models.enums import GraderKind, SubmissionStatus
from app.schemas.learning import ChallengeSummary, ExecutionPlan, ExerciseDetail
from app.services.submissions import PYTEST_ARGS


class ExerciseService:
    """Builds exercise responses without ever leaking hidden tests or solutions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, slug: str) -> Exercise:
        """Fetch an exercise or raise."""
        exercise = self._session.scalar(
            select(Exercise).options(selectinload(Exercise.hints)).where(Exercise.slug == slug)
        )
        if exercise is None:
            raise NotFoundError("Exercise", slug)
        return exercise

    def detail(self, user: User, slug: str) -> ExerciseDetail:
        """Everything the editor needs, plus this learner's state."""
        exercise = self._session.scalar(
            select(Exercise)
            .options(selectinload(Exercise.hints), selectinload(Exercise.lesson))
            .where(Exercise.slug == slug)
        )
        if exercise is None:
            raise NotFoundError("Exercise", slug)

        attempts = int(
            self._session.scalar(
                select(func.count())
                .select_from(Submission)
                .where(Submission.user_id == user.id, Submission.exercise_id == exercise.id)
            )
            or 0
        )
        best = float(
            self._session.scalar(
                select(func.coalesce(func.max(Submission.score), 0.0)).where(
                    Submission.user_id == user.id, Submission.exercise_id == exercise.id
                )
            )
            or 0.0
        )
        passed = bool(
            self._session.scalar(
                select(Submission.id).where(
                    Submission.user_id == user.id,
                    Submission.exercise_id == exercise.id,
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            )
        )
        hints_revealed = int(
            self._session.scalar(
                select(func.count())
                .select_from(HintReveal)
                .where(
                    HintReveal.user_id == user.id,
                    HintReveal.exercise_id == exercise.id,
                    HintReveal.source == "authored",
                )
            )
            or 0
        )
        solution_unlocked = bool(
            self._session.scalar(
                select(HintReveal.id).where(
                    HintReveal.user_id == user.id,
                    HintReveal.exercise_id == exercise.id,
                    HintReveal.source == "solution",
                )
            )
        )

        options = None
        if GraderKind(exercise.grader) is GraderKind.MULTIPLE_CHOICE:
            options = list(exercise.grader_config.get("options", []))

        return ExerciseDetail(
            slug=exercise.slug,
            title=exercise.title,
            prompt=exercise.prompt,
            kind=exercise.kind,
            level=exercise.level,
            difficulty=exercise.difficulty,
            estimated_minutes=exercise.estimated_minutes,
            xp_reward=exercise.xp_reward,
            starter_files=exercise.starter_files,
            grader=exercise.grader,
            concept_slugs=exercise.concept_slugs,
            lesson_slug=exercise.lesson.slug if exercise.lesson else None,
            hint_count=len(exercise.hints),
            hints_revealed=hints_revealed,
            solution_unlocked=solution_unlocked or passed,
            time_limit_minutes=exercise.time_limit_minutes,
            attempts=attempts,
            best_score=best,
            status="passed" if passed else "attempted" if attempts else "not_attempted",
            options=options,
            execution_plan=self._execution_plan(exercise),
        )

    @staticmethod
    def _execution_plan(exercise: Exercise) -> ExecutionPlan | None:
        """Describe how to run this exercise, for a client that executes it itself.

        Returns ``None`` unless the deployment has no server-side sandbox, so a
        Docker-backed deployment keeps its hidden tests hidden.
        """
        if not get_settings().client_side_execution:
            return None

        grader = GraderKind(exercise.grader)
        config = exercise.grader_config
        timeout = float(config.get("timeout_seconds", 0)) or get_settings().exec_timeout_seconds

        if grader is GraderKind.PYTEST:
            return ExecutionPlan(
                mode="pytest",
                pytest_args=list(PYTEST_ARGS),
                extra_files=dict(exercise.hidden_files),
                timeout_seconds=timeout,
            )
        if grader is GraderKind.STDOUT_MATCH:
            return ExecutionPlan(
                mode="script",
                entrypoint=str(config.get("entrypoint", "main.py")),
                stdin=str(config.get("stdin", "")),
                timeout_seconds=timeout,
            )
        # static_assert and multiple_choice are graded from the source alone.
        return None

    def list_challenges(
        self, user: User, *, kind: str | None = None, level: str | None = None
    ) -> list[ChallengeSummary]:
        """Challenge-flagged exercises."""
        query = select(Exercise).where(Exercise.is_challenge.is_(True))
        if kind:
            query = query.where(Exercise.challenge_kind == kind)
        if level:
            query = query.where(Exercise.level == level)
        exercises = self._session.scalars(query.order_by(Exercise.difficulty, Exercise.title)).all()
        return self._summaries(user, list(exercises))

    def search(
        self,
        user: User,
        *,
        concept: str | None = None,
        kind: str | None = None,
        level: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChallengeSummary]:
        """Browse the exercise catalogue."""
        query = select(Exercise)
        if kind:
            query = query.where(Exercise.kind == kind)
        if level:
            query = query.where(Exercise.level == level)
        exercises = list(
            self._session.scalars(
                query.order_by(Exercise.level, Exercise.difficulty).limit(limit).offset(offset)
            ).all()
        )
        if concept:
            exercises = [e for e in exercises if concept in e.concept_slugs]
        return self._summaries(user, exercises)

    def _summaries(self, user: User, exercises: list[Exercise]) -> list[ChallengeSummary]:
        if not exercises:
            return []
        ids = [exercise.id for exercise in exercises]
        rows = self._session.execute(
            select(Submission.exercise_id, func.max(Submission.score), func.count())
            .where(Submission.user_id == user.id, Submission.exercise_id.in_(ids))
            .group_by(Submission.exercise_id)
        ).all()
        best_by_id = {str(row[0]): (float(row[1] or 0.0), int(row[2] or 0)) for row in rows}
        passed = set(
            self._session.scalars(
                select(Submission.exercise_id).where(
                    Submission.user_id == user.id,
                    Submission.exercise_id.in_(ids),
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            ).all()
        )
        return [
            ChallengeSummary(
                slug=exercise.slug,
                title=exercise.title,
                prompt=exercise.prompt,
                kind=exercise.kind,
                level=exercise.level,
                difficulty=exercise.difficulty,
                estimated_minutes=exercise.estimated_minutes,
                xp_reward=exercise.xp_reward,
                position=exercise.position,
                is_challenge=exercise.is_challenge,
                challenge_kind=exercise.challenge_kind,
                time_limit_minutes=exercise.time_limit_minutes,
                status="passed"
                if exercise.id in passed
                else "attempted"
                if exercise.id in best_by_id
                else "not_attempted",
                best_score=best_by_id.get(exercise.id, (0.0, 0))[0],
            )
            for exercise in exercises
        ]
