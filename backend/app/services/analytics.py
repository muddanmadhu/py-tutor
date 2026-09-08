"""Learning analytics: the event stream and the aggregates built from it."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import (
    Concept,
    ConceptMastery,
    Exercise,
    LearningEvent,
    Lesson,
    LessonProgress,
    Submission,
    User,
)
from app.models.enums import LearningEventKind, SubmissionStatus


def record_event(
    session: Session,
    user: User,
    kind: LearningEventKind,
    *,
    subject_type: str | None = None,
    subject_slug: str | None = None,
    payload: dict[str, Any] | None = None,
) -> LearningEvent:
    """Append one analytics event.

    Events are written inside the caller's transaction: if the action rolls
    back, so does the record of it.
    """
    event = LearningEvent(
        user_id=user.id,
        kind=kind.value,
        subject_type=subject_type,
        subject_slug=subject_slug,
        payload=payload or {},
        occurred_at=utcnow(),
    )
    session.add(event)
    return event


@dataclass(frozen=True, slots=True)
class ExerciseDifficultyStat:
    """Observed difficulty of one exercise across all learners."""

    exercise_slug: str
    title: str
    attempts: int
    learners: int
    pass_rate: float
    average_attempts_to_pass: float
    hint_rate: float


@dataclass(frozen=True, slots=True)
class ConceptDifficultyStat:
    """How hard a concept proves to be in practice."""

    concept_slug: str
    concept_name: str
    learners: int
    average_score: float
    average_attempts: float
    top_misconceptions: list[tuple[str, int]]


class AnalyticsService:
    """Read-side aggregates over the event stream and submissions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- learner-scoped -----------------------------------------------------

    def activity_series(self, user_id: str, days: int = 30) -> list[dict[str, Any]]:
        """Daily counts of executions and passed submissions, oldest first."""
        since = utcnow() - timedelta(days=days)
        rows = self._session.execute(
            select(
                func.date(LearningEvent.occurred_at).label("day"),
                LearningEvent.kind,
                func.count().label("count"),
            )
            .where(LearningEvent.user_id == user_id, LearningEvent.occurred_at >= since)
            .group_by("day", LearningEvent.kind)
        ).all()

        by_day: dict[str, dict[str, int]] = {}
        for day, kind, count in rows:
            key = str(day)
            by_day.setdefault(key, {})[str(kind)] = int(count)

        series: list[dict[str, Any]] = []
        start = (utcnow() - timedelta(days=days - 1)).date()
        for offset in range(days):
            day = (start + timedelta(days=offset)).isoformat()
            counts = by_day.get(day, {})
            series.append(
                {
                    "date": day,
                    "runs": counts.get(LearningEventKind.CODE_EXECUTED.value, 0),
                    "submissions": counts.get(LearningEventKind.SUBMISSION_GRADED.value, 0),
                    "lessons": counts.get(LearningEventKind.LESSON_COMPLETED.value, 0),
                    "hints": counts.get(LearningEventKind.HINT_REVEALED.value, 0),
                }
            )
        return series

    def repeated_mistakes(self, user_id: str, limit: int = 8) -> list[dict[str, Any]]:
        """Misconceptions this learner keeps hitting, most frequent first."""
        rows = self._session.scalars(
            select(ConceptMastery).where(ConceptMastery.user_id == user_id)
        ).all()
        tally: Counter[str] = Counter()
        for row in rows:
            tally.update(row.misconception_counts)
        return [
            {"misconception": slug, "count": count, "label": humanise_misconception(slug)}
            for slug, count in tally.most_common(limit)
        ]

    def learner_summary(self, user_id: str) -> dict[str, Any]:
        """Headline counters for the dashboard."""
        graded = self._session.execute(
            select(
                func.count(Submission.id),
                func.sum(case((Submission.status == SubmissionStatus.PASSED.value, 1), else_=0)),
                func.count(func.distinct(Submission.exercise_id)),
            ).where(Submission.user_id == user_id)
        ).one()
        total_attempts = int(graded[0] or 0)
        passed_attempts = int(graded[1] or 0)
        distinct_exercises = int(graded[2] or 0)

        exercises_passed = int(
            self._session.scalar(
                select(func.count(func.distinct(Submission.exercise_id))).where(
                    Submission.user_id == user_id,
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            )
            or 0
        )
        lessons_completed = int(
            self._session.scalar(
                select(func.count())
                .select_from(LessonProgress)
                .where(LessonProgress.user_id == user_id, LessonProgress.status == "completed")
            )
            or 0
        )
        lessons_total = int(self._session.scalar(select(func.count()).select_from(Lesson)) or 0)

        return {
            "total_attempts": total_attempts,
            "passed_attempts": passed_attempts,
            "attempt_accuracy": round(passed_attempts / total_attempts, 4)
            if total_attempts
            else 0.0,
            "exercises_attempted": distinct_exercises,
            "exercises_passed": exercises_passed,
            "lessons_completed": lessons_completed,
            "lessons_total": lessons_total,
        }

    # -- cohort-scoped ------------------------------------------------------

    def hardest_exercises(self, limit: int = 10) -> list[ExerciseDifficultyStat]:
        """Exercises with the lowest pass rate — the curriculum's rough edges."""
        rows = self._session.execute(
            select(
                Exercise.slug,
                Exercise.title,
                func.count(Submission.id),
                func.count(func.distinct(Submission.user_id)),
                func.sum(case((Submission.status == SubmissionStatus.PASSED.value, 1), else_=0)),
                func.sum(case((Submission.hints_used > 0, 1), else_=0)),
            )
            .join(Submission, Submission.exercise_id == Exercise.id)
            .group_by(Exercise.id, Exercise.slug, Exercise.title)
            .having(func.count(Submission.id) >= 3)
        ).all()

        stats = [
            ExerciseDifficultyStat(
                exercise_slug=str(slug),
                title=str(title),
                attempts=int(attempts or 0),
                learners=int(learners or 0),
                pass_rate=round(int(passed or 0) / int(attempts or 1), 4),
                average_attempts_to_pass=round(int(attempts or 0) / max(1, int(passed or 0)), 2)
                if passed
                else float(attempts or 0),
                hint_rate=round(int(hinted or 0) / int(attempts or 1), 4),
            )
            for slug, title, attempts, learners, passed, hinted in rows
        ]
        stats.sort(key=lambda stat: (stat.pass_rate, -stat.attempts))
        return stats[:limit]

    def hardest_concepts(self, limit: int = 10) -> list[ConceptDifficultyStat]:
        """Concepts where mastery is slowest to arrive."""
        rows = self._session.execute(
            select(
                Concept.slug,
                Concept.name,
                func.count(ConceptMastery.id),
                func.avg(ConceptMastery.score),
                func.avg(ConceptMastery.attempts),
            )
            .join(ConceptMastery, ConceptMastery.concept_id == Concept.id)
            .group_by(Concept.id, Concept.slug, Concept.name)
        ).all()

        misconceptions_by_concept: dict[str, Counter[str]] = {}
        for record, concept_slug in self._session.execute(
            select(ConceptMastery, Concept.slug).join(
                Concept, Concept.id == ConceptMastery.concept_id
            )
        ).all():
            misconceptions_by_concept.setdefault(str(concept_slug), Counter()).update(
                record.misconception_counts
            )

        stats = [
            ConceptDifficultyStat(
                concept_slug=str(slug),
                concept_name=str(name),
                learners=int(learners or 0),
                average_score=round(float(avg_score or 0.0), 4),
                average_attempts=round(float(avg_attempts or 0.0), 2),
                top_misconceptions=misconceptions_by_concept.get(str(slug), Counter()).most_common(
                    3
                ),
            )
            for slug, name, learners, avg_score, avg_attempts in rows
        ]
        stats.sort(key=lambda stat: stat.average_score)
        return stats[:limit]

    def drop_off_points(self, limit: int = 10) -> list[dict[str, Any]]:
        """Lessons learners start but do not finish.

        A high drop-off rate usually means the lesson's first exercise is too
        big a step, not that the topic is inherently hard.
        """
        rows = self._session.execute(
            select(
                Lesson.slug,
                Lesson.title,
                func.count(LessonProgress.id),
                func.sum(case((LessonProgress.status == "completed", 1), else_=0)),
            )
            .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .group_by(Lesson.id, Lesson.slug, Lesson.title)
            .having(func.count(LessonProgress.id) >= 3)
        ).all()

        points: list[dict[str, Any]] = [
            {
                "lesson_slug": str(slug),
                "title": str(title),
                "started": int(started or 0),
                "completed": int(completed or 0),
                "drop_off_rate": round(1 - int(completed or 0) / int(started or 1), 4),
            }
            for slug, title, started, completed in rows
        ]
        points.sort(key=lambda item: float(item["drop_off_rate"]), reverse=True)
        return points[:limit]

    def platform_summary(self) -> dict[str, Any]:
        """Counters for the author/admin analytics view."""
        active_since = datetime.now(UTC) - timedelta(days=7)
        return {
            "learners": int(self._session.scalar(select(func.count()).select_from(User)) or 0),
            "active_learners_7d": int(
                self._session.scalar(
                    select(func.count(func.distinct(LearningEvent.user_id))).where(
                        LearningEvent.occurred_at >= active_since
                    )
                )
                or 0
            ),
            "submissions": int(
                self._session.scalar(select(func.count()).select_from(Submission)) or 0
            ),
            "lessons": int(self._session.scalar(select(func.count()).select_from(Lesson)) or 0),
            "exercises": int(self._session.scalar(select(func.count()).select_from(Exercise)) or 0),
            "concepts": int(self._session.scalar(select(func.count()).select_from(Concept)) or 0),
        }


_MISCONCEPTION_LABELS = {
    "output-mismatch": "Output does not match the specification exactly",
    "syntax-error": "Code does not parse",
    "indentation": "Block structure / indentation",
    "undefined-name": "Using a name before defining it",
    "type-mismatch": "Mixing incompatible types (often str vs int)",
    "value-conversion": "Converting a value that cannot be converted",
    "off-by-one": "Off-by-one indexing",
    "missing-key": "Assuming a dictionary key exists",
    "wrong-attribute": "Calling a method the object does not have",
    "unguarded-division": "Dividing without checking for zero",
    "missing-import": "Using a module that was never imported or installed",
    "runaway-recursion": "Recursion without a base case",
    "infinite-loop": "Loop condition never becomes false",
    "mutable-default": "Mutable default argument shared between calls",
    "late-binding-closure": "Closure captures the variable, not its value",
    "aliasing": "Two names referring to the same object",
    "shallow-copy": "Copying only the outer container",
    "structural-requirement": "Solution does not meet the structural brief",
    "concept-confusion": "Concept not yet distinguished from a neighbouring one",
    "collection-error": "Tests could not run against the submitted code",
    "empty-submission": "Nothing was submitted",
    "runtime-error": "Unhandled runtime error",
}


def humanise_misconception(slug: str) -> str:
    """Human-readable label for a misconception id."""
    return _MISCONCEPTION_LABELS.get(slug, slug.replace("-", " ").capitalize())
