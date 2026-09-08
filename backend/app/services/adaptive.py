"""Adaptive learning: deciding what the learner should do next.

The engine answers two questions.

**What should I study next?**
Walk the concept prerequisite graph. A concept is *ready* when every
prerequisite is at or above the readiness threshold. Among ready concepts,
prefer those that are weakest but already started (finish what you began),
then those that unlock the most downstream material.

**I keep failing this — now what?**
Repeated failure on one exercise triggers the remediation ladder from spec §35:
identify the misconception, show a targeted explanation, drop to an easier item
on the same concept, then a similar item, then step the difficulty back up and
retest. The ladder is expressed as an explicit state machine so the learner's
position in it is inspectable rather than emergent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Concept,
    Exercise,
    Lesson,
    LessonProgress,
    Submission,
    User,
)
from app.models.enums import SubmissionStatus
from app.services.analytics import humanise_misconception
from app.services.mastery import MasteryService, MasteryView

#: A prerequisite counts as satisfied at this mastery score.
READINESS_THRESHOLD = 0.6
#: Below this, a started concept is treated as needing more work.
NEEDS_WORK_THRESHOLD = 0.7
#: Consecutive failures on one exercise before remediation kicks in.
STRUGGLE_THRESHOLD = 3


class RecommendationKind(StrEnum):
    """Why the engine is suggesting this next step."""

    REMEDIATE = "remediate"
    """You are stuck; here is targeted help."""

    REVIEW = "review"
    """Mastery has decayed; refresh it."""

    CONTINUE = "continue"
    """Carry on with the lesson you started."""

    ADVANCE = "advance"
    """Prerequisites met; here is new material."""

    PROJECT = "project"
    """Enough concepts are solid to build something."""


@dataclass(frozen=True, slots=True)
class Recommendation:
    """A single suggested next step, ready to render as a card."""

    kind: RecommendationKind
    title: str
    reason: str
    lesson_slug: str | None = None
    exercise_slug: str | None = None
    concept_slug: str | None = None
    priority: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the API."""
        return {
            "kind": self.kind.value,
            "title": self.title,
            "reason": self.reason,
            "lesson_slug": self.lesson_slug,
            "exercise_slug": self.exercise_slug,
            "concept_slug": self.concept_slug,
            "priority": round(self.priority, 4),
        }


class RemediationStage(StrEnum):
    """Where a struggling learner is on the remediation ladder."""

    EXPLAIN = "targeted_explanation"
    EASIER = "easier_exercise"
    SIMILAR = "similar_exercise"
    RETEST = "retest"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class RemediationPlan:
    """The adaptive response to repeated failure."""

    stage: RemediationStage
    misconception: str | None
    explanation: str
    concept_slug: str | None
    next_exercise_slug: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the API."""
        return {
            "stage": self.stage.value,
            "misconception": self.misconception,
            "misconception_label": humanise_misconception(self.misconception)
            if self.misconception
            else None,
            "explanation": self.explanation,
            "concept_slug": self.concept_slug,
            "next_exercise_slug": self.next_exercise_slug,
            "message": self.message,
        }


class AdaptiveService:
    """Recommends next steps and builds remediation plans."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mastery = MasteryService(session)

    # -- recommendations ----------------------------------------------------

    def recommend(self, user: User, limit: int = 5) -> list[Recommendation]:
        """Return the learner's prioritised next steps."""
        views = self._mastery.view_by_slug(user.id)
        recommendations: list[Recommendation] = []

        recommendations.extend(self._struggling_recommendations(user))
        recommendations.extend(self._review_recommendations(views))
        recommendations.extend(self._continue_recommendations(user))
        recommendations.extend(self._advance_recommendations(user, views))

        seen: set[tuple[str | None, str | None]] = set()
        unique: list[Recommendation] = []
        for item in sorted(recommendations, key=lambda r: r.priority, reverse=True):
            key = (item.lesson_slug, item.exercise_slug)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique[:limit]

    def _struggling_recommendations(self, user: User) -> list[Recommendation]:
        out: list[Recommendation] = []
        for exercise, failures in self._struggling_exercises(user.id):
            out.append(
                Recommendation(
                    kind=RecommendationKind.REMEDIATE,
                    title=f"Get unstuck: {exercise.title}",
                    reason=f"{failures} attempts without a pass. A targeted explanation and an "
                    "easier step will help more than another try.",
                    lesson_slug=exercise.lesson.slug if exercise.lesson else None,
                    exercise_slug=exercise.slug,
                    concept_slug=exercise.concept_slugs[0] if exercise.concept_slugs else None,
                    priority=1.0 + 0.05 * failures,
                )
            )
        return out

    @staticmethod
    def _review_recommendations(views: dict[str, MasteryView]) -> list[Recommendation]:
        out: list[Recommendation] = []
        for view in views.values():
            if view.attempts >= 2 and 0.3 <= view.score < NEEDS_WORK_THRESHOLD:
                out.append(
                    Recommendation(
                        kind=RecommendationKind.REVIEW,
                        title=f"Review {view.concept_name}",
                        reason=f"Mastery is at {view.percent}%. A short practice session "
                        "would consolidate it.",
                        concept_slug=view.concept_slug,
                        priority=0.8 * (1.0 - view.score),
                    )
                )
        return out

    def _continue_recommendations(self, user: User) -> list[Recommendation]:
        rows = self._session.execute(
            select(LessonProgress, Lesson)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(LessonProgress.user_id == user.id, LessonProgress.status == "in_progress")
            .order_by(LessonProgress.updated_at.desc())
            .limit(3)
        ).all()
        return [
            Recommendation(
                kind=RecommendationKind.CONTINUE,
                title=f"Continue: {lesson.title}",
                reason=f"{progress.exercises_completed} of {progress.exercises_total} "
                "exercises done.",
                lesson_slug=lesson.slug,
                priority=0.75,
            )
            for progress, lesson in rows
        ]

    def _advance_recommendations(
        self, user: User, views: dict[str, MasteryView]
    ) -> list[Recommendation]:
        completed_lesson_ids = set(
            self._session.scalars(
                select(LessonProgress.lesson_id).where(
                    LessonProgress.user_id == user.id, LessonProgress.status == "completed"
                )
            ).all()
        )
        lessons = self._session.scalars(
            select(Lesson)
            .options(selectinload(Lesson.concepts).selectinload(Concept.prerequisites))
            .order_by(Lesson.position)
        ).all()

        out: list[Recommendation] = []
        for lesson in lessons:
            if lesson.id in completed_lesson_ids:
                continue
            blockers = self._unmet_prerequisites(lesson, views)
            if blockers:
                continue
            out.append(
                Recommendation(
                    kind=RecommendationKind.ADVANCE,
                    title=f"Start: {lesson.title}",
                    reason="You have the prerequisites for this. "
                    f"About {lesson.estimated_minutes} minutes.",
                    lesson_slug=lesson.slug,
                    priority=0.7 - min(0.2, lesson.position * 0.001),
                )
            )
            if len(out) >= 3:
                break
        return out

    @staticmethod
    def _unmet_prerequisites(lesson: Lesson, views: dict[str, MasteryView]) -> list[str]:
        """Prerequisite concept slugs the learner has not yet reached readiness on."""
        unmet: list[str] = []
        for concept in lesson.concepts:
            for prerequisite in concept.prerequisites:
                view = views.get(prerequisite.slug)
                if view is None or view.score < READINESS_THRESHOLD:
                    unmet.append(prerequisite.slug)
        return sorted(set(unmet))

    def _struggling_exercises(self, user_id: str) -> list[tuple[Exercise, int]]:
        """Exercises with repeated failures and no pass."""
        rows = self._session.execute(
            select(Submission.exercise_id, func.count(Submission.id))
            .where(Submission.user_id == user_id)
            .group_by(Submission.exercise_id)
            .having(func.count(Submission.id) >= STRUGGLE_THRESHOLD)
        ).all()
        struggling: list[tuple[Exercise, int]] = []
        for exercise_id, attempts in rows:
            passed = self._session.scalar(
                select(Submission.id).where(
                    Submission.user_id == user_id,
                    Submission.exercise_id == exercise_id,
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            )
            if passed:
                continue
            exercise = self._session.get(Exercise, exercise_id)
            if exercise is not None:
                struggling.append((exercise, int(attempts)))
        return struggling

    # -- remediation --------------------------------------------------------

    def remediation_plan(self, user: User, exercise_slug: str) -> RemediationPlan | None:
        """Build a remediation plan when a learner is stuck, else ``None``."""
        exercise = self._session.scalar(select(Exercise).where(Exercise.slug == exercise_slug))
        if exercise is None:
            return None

        attempts = list(
            self._session.scalars(
                select(Submission)
                .where(Submission.user_id == user.id, Submission.exercise_id == exercise.id)
                .order_by(Submission.created_at.desc())
                .limit(6)
            ).all()
        )
        if any(a.status == SubmissionStatus.PASSED.value for a in attempts):
            return RemediationPlan(
                stage=RemediationStage.RESOLVED,
                misconception=None,
                explanation="",
                concept_slug=exercise.concept_slugs[0] if exercise.concept_slugs else None,
                next_exercise_slug=None,
                message="You've already passed this one.",
            )
        if len(attempts) < STRUGGLE_THRESHOLD:
            return None

        misconception = self._dominant_misconception(attempts)
        concept_slug = exercise.concept_slugs[0] if exercise.concept_slugs else None
        explanation = self._explanation_for(concept_slug, misconception)

        easier = self._find_sibling(exercise, easier=True)
        if easier is not None:
            return RemediationPlan(
                stage=RemediationStage.EASIER,
                misconception=misconception,
                explanation=explanation,
                concept_slug=concept_slug,
                next_exercise_slug=easier.slug,
                message=(
                    "Let's take a smaller step. This exercise practises the same idea with "
                    "less going on, so the concept stands out."
                ),
            )

        similar = self._find_sibling(exercise, easier=False)
        if similar is not None:
            return RemediationPlan(
                stage=RemediationStage.SIMILAR,
                misconception=misconception,
                explanation=explanation,
                concept_slug=concept_slug,
                next_exercise_slug=similar.slug,
                message="Try this variation — it exercises the same concept from a "
                "different angle.",
            )

        return RemediationPlan(
            stage=RemediationStage.EXPLAIN,
            misconception=misconception,
            explanation=explanation,
            concept_slug=concept_slug,
            next_exercise_slug=None,
            message="Here's a targeted explanation of what's tripping you up. Re-read it, "
            "then come back to the exercise.",
        )

    @staticmethod
    def _dominant_misconception(attempts: list[Submission]) -> str | None:
        tally: dict[str, int] = {}
        for attempt in attempts:
            for slug in attempt.misconceptions:
                tally[slug] = tally.get(slug, 0) + 1
        if not tally:
            return None
        return max(tally.items(), key=lambda item: item[1])[0]

    def _explanation_for(self, concept_slug: str | None, misconception: str | None) -> str:
        """Prefer the author's explanation for this misconception, else a generic one."""
        if concept_slug and misconception:
            concept = self._session.scalar(select(Concept).where(Concept.slug == concept_slug))
            if concept:
                for entry in concept.common_misconceptions:
                    if entry.get("slug") == misconception:
                        return str(entry.get("explanation", ""))
        if misconception:
            return (
                f"The pattern in your attempts points at one thing: "
                f"**{humanise_misconception(misconception)}**. Fix that and the rest usually "
                "falls into place."
            )
        return (
            "Your attempts don't share an obvious pattern, which often means the brief itself "
            "isn't clear yet. Re-read the requirement and write down, in words, what the code "
            "must produce before changing any more of it."
        )

    def _find_sibling(self, exercise: Exercise, *, easier: bool) -> Exercise | None:
        """Find another exercise on the same concept, easier or comparable."""
        if not exercise.concept_slugs:
            return None
        candidates = self._session.scalars(
            select(Exercise).where(Exercise.id != exercise.id).order_by(Exercise.difficulty)
        ).all()
        overlapping = [
            candidate
            for candidate in candidates
            if set(candidate.concept_slugs) & set(exercise.concept_slugs)
        ]
        if easier:
            easier_ones = [c for c in overlapping if c.difficulty < exercise.difficulty - 0.05]
            return easier_ones[-1] if easier_ones else None
        similar = [c for c in overlapping if abs(c.difficulty - exercise.difficulty) <= 0.15]
        return similar[0] if similar else None

    # -- readiness ----------------------------------------------------------

    def concept_readiness(self, user_id: str) -> list[dict[str, Any]]:
        """For every concept: score, whether prerequisites are met, and blockers."""
        views = self._mastery.view_by_slug(user_id)
        concepts = self._session.scalars(
            select(Concept).options(selectinload(Concept.prerequisites)).order_by(Concept.slug)
        ).all()
        out: list[dict[str, Any]] = []
        for concept in concepts:
            blockers = [
                prerequisite.slug
                for prerequisite in concept.prerequisites
                if views.get(prerequisite.slug) is None
                or views[prerequisite.slug].score < READINESS_THRESHOLD
            ]
            view = views.get(concept.slug)
            out.append(
                {
                    "concept_slug": concept.slug,
                    "concept_name": concept.name,
                    "level": concept.level,
                    "category": concept.category,
                    "score": view.score if view else 0.0,
                    "band": view.band.value if view else "not_started",
                    "ready": not blockers,
                    "blocked_by": blockers,
                }
            )
        return out
