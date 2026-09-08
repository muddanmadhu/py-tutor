"""The mastery engine.

Why not "lessons completed"
---------------------------
Completion counts reward clicking *Next*. This engine estimates whether a
learner can *use* a concept, from evidence that is hard to fake:

* correctness, weighted by how hard the item was
* whether it was right on the first attempt, unaided
* how much hint scaffolding was consumed
* whether the solution was revealed
* how the time taken compares with the item's estimate
* how long ago the concept was last exercised (retention decay)

The model
---------
For each attempt we compute an *evidence value* ``e ∈ [0, 1]``::

    e = raw_score × hint_discount × solution_discount × pace_factor

then blend it into the stored score with a learning rate that shrinks as
confidence grows, so early evidence moves the needle quickly and later evidence
refines rather than whipsaws::

    α       = base_rate × (1 − 0.6 × confidence)
    score'  = score + α × (target(e, difficulty) − score)

``target`` lifts credit for succeeding on a hard item and reduces the penalty
for failing one — getting a metaclass exercise wrong should not cost as much as
fumbling variable assignment.

Confidence rises with each independent piece of evidence and never reaches 1::

    confidence' = confidence + (1 − confidence) × 0.22

On read, a retention factor is applied. Recall decays roughly exponentially;
the time constant grows with confidence, so well-established concepts fade
slowly and shaky ones fade fast. Decay is applied on read rather than written
into the row, so a learner who returns after a month sees an honest number
without a background job having to rewrite every row.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import Concept, ConceptMastery, User

# --- Tunables --------------------------------------------------------------
BASE_LEARNING_RATE = 0.45
CONFIDENCE_GAIN = 0.22
#: Days after which an unpractised concept at zero confidence retains ~37%.
BASE_RETENTION_TAU_DAYS = 12.0
#: Multiplier on tau at full confidence (well-learned material fades slowly).
MAX_RETENTION_STRETCH = 9.0
#: Retention never drives a score below this fraction of its stored value.
RETENTION_FLOOR = 0.55
#: Score at or above which a concept counts as mastered…
MASTERY_THRESHOLD = 0.85
#: …provided there is at least this much evidence behind it.
MASTERY_MIN_ATTEMPTS = 3
MASTERY_MIN_CONFIDENCE = 0.5

HINT_PENALTY_PER_LEVEL = 0.12
SOLUTION_PENALTY = 0.55


class MasteryBand(StrEnum):
    """Human-readable mastery bands used across the UI."""

    NOT_STARTED = "not_started"
    NOVICE = "novice"
    LEARNING = "learning"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    MASTERED = "mastered"


@dataclass(frozen=True, slots=True)
class Evidence:
    """One graded observation about a learner's command of a concept."""

    raw_score: float
    """Grader score in [0, 1]."""

    difficulty: float = 0.5
    """Item difficulty in [0, 1]."""

    first_attempt: bool = True
    hints_used: int = 0
    solution_viewed: bool = False
    time_spent_seconds: int = 0
    expected_seconds: int = 0

    def value(self) -> float:
        """Collapse the observation into a single [0, 1] evidence figure."""
        score = _clamp(self.raw_score)
        hint_discount = max(0.35, 1.0 - HINT_PENALTY_PER_LEVEL * max(0, self.hints_used))
        solution_discount = SOLUTION_PENALTY if self.solution_viewed else 1.0
        return _clamp(score * hint_discount * solution_discount * self._pace_factor())

    def _pace_factor(self) -> float:
        """Mild credit for fluency, mild discount for a long struggle.

        Capped tightly on both sides: speed is weak evidence compared with
        correctness, and we never want to push learners to rush.
        """
        if not self.expected_seconds or not self.time_spent_seconds or self.raw_score <= 0:
            return 1.0
        ratio = self.time_spent_seconds / self.expected_seconds
        if ratio <= 0.6:
            return 1.05
        if ratio >= 3.0:
            return 0.9
        return 1.0


@dataclass(frozen=True, slots=True)
class MasteryView:
    """Decayed, presentation-ready mastery for one concept."""

    concept_slug: str
    concept_name: str
    category: str
    level: str
    score: float
    confidence: float
    band: MasteryBand
    attempts: int
    accuracy: float
    hints_used: int
    last_practiced_at: datetime | None
    is_mastered: bool
    top_misconceptions: list[str]

    @property
    def percent(self) -> int:
        """Score as a 0–100 integer for progress bars."""
        return round(self.score * 100)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def band_for(score: float, attempts: int = 1) -> MasteryBand:
    """Map a score onto a band."""
    if attempts == 0:
        return MasteryBand.NOT_STARTED
    if score >= MASTERY_THRESHOLD:
        return MasteryBand.MASTERED
    if score >= 0.7:
        return MasteryBand.PROFICIENT
    if score >= 0.5:
        return MasteryBand.COMPETENT
    if score >= 0.25:
        return MasteryBand.LEARNING
    return MasteryBand.NOVICE


def target_for(evidence_value: float, difficulty: float) -> float:
    """Where this evidence says the score *should* sit.

    Succeeding on a difficult item is stronger proof of mastery than succeeding
    on an easy one, and failing a difficult item is weaker proof of ignorance.
    Both effects are bounded so difficulty can never manufacture mastery on its
    own.
    """
    difficulty = _clamp(difficulty)
    if evidence_value >= 0.5:
        # Success: bonus scales with difficulty, up to +0.15.
        return _clamp(evidence_value + 0.15 * difficulty * evidence_value)
    # Failure: cushion scales with difficulty, up to +0.20 of the shortfall.
    return _clamp(evidence_value + 0.20 * difficulty * (1.0 - evidence_value))


def retention_factor(last_practiced_at: datetime | None, confidence: float) -> float:
    """Exponential forgetting curve, floored so scores never collapse to zero."""
    if last_practiced_at is None:
        return 1.0
    if last_practiced_at.tzinfo is None:
        last_practiced_at = last_practiced_at.replace(tzinfo=UTC)
    days = max(0.0, (datetime.now(UTC) - last_practiced_at).total_seconds() / 86_400)
    tau = BASE_RETENTION_TAU_DAYS * (1.0 + MAX_RETENTION_STRETCH * _clamp(confidence))
    return max(RETENTION_FLOOR, math.exp(-days / tau))


class MasteryService:
    """Reads and updates concept mastery."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- writes -------------------------------------------------------------

    def record(
        self,
        user: User,
        concept_slugs: list[str],
        evidence: Evidence,
        misconceptions: list[str] | None = None,
    ) -> list[ConceptMastery]:
        """Fold ``evidence`` into every named concept and return the rows."""
        if not concept_slugs:
            return []
        concepts = self._session.scalars(
            select(Concept).where(Concept.slug.in_(concept_slugs))
        ).all()
        updated: list[ConceptMastery] = []
        for concept in concepts:
            record = self._get_or_create(user.id, concept.id)
            self._apply(record, concept, evidence, misconceptions or [])
            updated.append(record)
        self._session.flush()
        return updated

    def _apply(
        self,
        record: ConceptMastery,
        concept: Concept,
        evidence: Evidence,
        misconceptions: list[str],
    ) -> None:
        """Mutate ``record`` in place with one new observation."""
        # Decay first: the update should build on the learner's *current* recall,
        # not on a stale peak from six weeks ago.
        decayed = record.score * retention_factor(record.last_practiced_at, record.confidence)

        value = evidence.value()
        target = target_for(value, concept.difficulty)
        alpha = BASE_LEARNING_RATE * (1.0 - 0.6 * _clamp(record.confidence))
        record.score = _clamp(decayed + alpha * (target - decayed))
        record.confidence = _clamp(record.confidence + (1.0 - record.confidence) * CONFIDENCE_GAIN)

        record.attempts += 1
        if evidence.raw_score >= 0.999:
            record.correct_attempts += 1
            if evidence.first_attempt and evidence.hints_used == 0 and not evidence.solution_viewed:
                record.first_try_correct += 1
        record.hints_used += max(0, evidence.hints_used)
        if evidence.solution_viewed:
            record.solutions_viewed += 1
        record.total_time_seconds += max(0, evidence.time_spent_seconds)
        record.last_practiced_at = utcnow()

        if misconceptions:
            counts = dict(record.misconception_counts)
            for slug in misconceptions:
                counts[slug] = counts.get(slug, 0) + 1
            record.misconception_counts = counts

        if self._qualifies_as_mastered(record) and record.mastered_at is None:
            record.mastered_at = utcnow()
        elif not self._qualifies_as_mastered(record):
            # Mastery can be lost; the badge should not outlive the evidence.
            record.mastered_at = None

    @staticmethod
    def _qualifies_as_mastered(record: ConceptMastery) -> bool:
        return (
            record.score >= MASTERY_THRESHOLD
            and record.attempts >= MASTERY_MIN_ATTEMPTS
            and record.confidence >= MASTERY_MIN_CONFIDENCE
        )

    def _get_or_create(self, user_id: str, concept_id: str) -> ConceptMastery:
        record = self._session.scalar(
            select(ConceptMastery).where(
                ConceptMastery.user_id == user_id, ConceptMastery.concept_id == concept_id
            )
        )
        if record is None:
            record = ConceptMastery(user_id=user_id, concept_id=concept_id)
            self._session.add(record)
            self._session.flush()
        return record

    # -- reads --------------------------------------------------------------

    def view_for(self, user_id: str) -> list[MasteryView]:
        """Return decayed mastery for every concept the learner has touched."""
        rows = self._session.execute(
            select(ConceptMastery, Concept)
            .join(Concept, Concept.id == ConceptMastery.concept_id)
            .where(ConceptMastery.user_id == user_id)
            .order_by(Concept.level, Concept.slug)
        ).all()
        return [self._to_view(record, concept) for record, concept in rows]

    def view_by_slug(self, user_id: str) -> dict[str, MasteryView]:
        """Mastery views keyed by concept slug."""
        return {view.concept_slug: view for view in self.view_for(user_id)}

    @staticmethod
    def _to_view(record: ConceptMastery, concept: Concept) -> MasteryView:
        effective = record.score * retention_factor(record.last_practiced_at, record.confidence)
        ranked = sorted(record.misconception_counts.items(), key=lambda item: item[1], reverse=True)
        return MasteryView(
            concept_slug=concept.slug,
            concept_name=concept.name,
            category=concept.category,
            level=concept.level,
            score=round(effective, 4),
            confidence=round(record.confidence, 4),
            band=band_for(effective, record.attempts),
            attempts=record.attempts,
            accuracy=round(record.accuracy, 4),
            hints_used=record.hints_used,
            last_practiced_at=record.last_practiced_at,
            is_mastered=record.mastered_at is not None,
            top_misconceptions=[slug for slug, _ in ranked[:3]],
        )

    def overall_mastery(self, user_id: str) -> float:
        """Concept-weighted mastery across the whole curriculum.

        Untouched concepts count as zero: overall mastery is a measure of the
        curriculum conquered, not of average performance on attempted items.
        """
        concepts = self._session.scalars(select(Concept)).all()
        denominator = sum(c.weight for c in concepts)
        if not denominator:
            return 0.0
        views = self.view_by_slug(user_id)
        weighted = sum(views[c.slug].score * c.weight for c in concepts if c.slug in views)
        return round(weighted / denominator, 4)

    def weak_concepts(self, user_id: str, limit: int = 5) -> list[MasteryView]:
        """Practised concepts with the lowest scores — the study list."""
        practised = [view for view in self.view_for(user_id) if view.attempts > 0]
        practised.sort(key=lambda view: (view.score, -view.attempts))
        return practised[:limit]

    def strong_concepts(self, user_id: str, limit: int = 5) -> list[MasteryView]:
        """Highest-scoring concepts — used for encouragement and certification."""
        practised = [view for view in self.view_for(user_id) if view.attempts > 0]
        practised.sort(key=lambda view: view.score, reverse=True)
        return practised[:limit]
