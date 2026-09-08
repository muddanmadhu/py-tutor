"""Tests for the mastery engine.

These pin down the behaviour that makes mastery different from completion:
unaided success moves faster than hinted success, difficulty is accounted for,
mastery decays, and mastery can be lost.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models import Concept, ConceptMastery
from app.services.mastery import (
    MASTERY_THRESHOLD,
    Evidence,
    MasteryBand,
    MasteryService,
    band_for,
    retention_factor,
    target_for,
)


@pytest.fixture()
def concept(session):
    record = Concept(
        slug="test-concept",
        name="Test Concept",
        description="",
        category="fundamentals",
        difficulty=0.5,
        weight=1.0,
    )
    session.add(record)
    session.flush()
    return record


class TestEvidence:
    def test_perfect_unaided_attempt_is_full_value(self):
        assert Evidence(raw_score=1.0).value() == pytest.approx(1.0)

    def test_hints_discount_the_evidence(self):
        unaided = Evidence(raw_score=1.0).value()
        hinted = Evidence(raw_score=1.0, hints_used=2).value()
        assert hinted < unaided

    def test_solution_discounts_heavily(self):
        hinted = Evidence(raw_score=1.0, hints_used=1).value()
        revealed = Evidence(raw_score=1.0, solution_viewed=True).value()
        assert revealed < hinted

    def test_hint_discount_has_a_floor(self):
        assert Evidence(raw_score=1.0, hints_used=99).value() >= 0.3

    def test_fast_work_earns_a_small_bonus(self):
        steady = Evidence(raw_score=1.0, time_spent_seconds=600, expected_seconds=600).value()
        quick = Evidence(raw_score=1.0, time_spent_seconds=120, expected_seconds=600).value()
        assert quick >= steady

    def test_value_is_bounded(self):
        assert Evidence(raw_score=5.0).value() <= 1.0
        assert Evidence(raw_score=-3.0).value() >= 0.0


class TestTargets:
    def test_success_on_a_hard_item_is_worth_more(self):
        assert target_for(0.9, difficulty=0.9) > target_for(0.9, difficulty=0.1)

    def test_failure_on_a_hard_item_hurts_less(self):
        assert target_for(0.0, difficulty=0.9) > target_for(0.0, difficulty=0.1)

    def test_targets_stay_in_range(self):
        for value in (0.0, 0.25, 0.5, 0.75, 1.0):
            for difficulty in (0.0, 0.5, 1.0):
                assert 0.0 <= target_for(value, difficulty) <= 1.0


class TestRetention:
    def test_no_decay_without_practice_history(self):
        assert retention_factor(None, confidence=0.5) == 1.0

    def test_recent_practice_barely_decays(self):
        recent = datetime.now(UTC) - timedelta(hours=1)
        assert retention_factor(recent, confidence=0.5) > 0.98

    def test_decay_grows_with_time(self):
        week = datetime.now(UTC) - timedelta(days=7)
        month = datetime.now(UTC) - timedelta(days=30)
        assert retention_factor(month, confidence=0.2) < retention_factor(week, confidence=0.2)

    def test_confidence_slows_decay(self):
        long_ago = datetime.now(UTC) - timedelta(days=30)
        assert retention_factor(long_ago, confidence=0.95) > retention_factor(
            long_ago, confidence=0.05
        )

    def test_decay_never_reaches_zero(self):
        ancient = datetime.now(UTC) - timedelta(days=3650)
        assert retention_factor(ancient, confidence=0.0) > 0.5


class TestBands:
    def test_untouched_concept_is_not_started(self):
        assert band_for(0.0, attempts=0) is MasteryBand.NOT_STARTED

    def test_high_score_is_mastered(self):
        assert band_for(0.95, attempts=5) is MasteryBand.MASTERED

    def test_bands_are_monotonic(self):
        order = [
            MasteryBand.NOVICE,
            MasteryBand.LEARNING,
            MasteryBand.COMPETENT,
            MasteryBand.PROFICIENT,
            MasteryBand.MASTERED,
        ]
        observed = [band_for(score, attempts=3) for score in (0.1, 0.3, 0.6, 0.8, 0.95)]
        assert observed == order


class TestMasteryService:
    def test_first_success_moves_the_score(self, session, user, concept):
        service = MasteryService(session)
        service.record(user, [concept.slug], Evidence(raw_score=1.0))
        view = service.view_by_slug(user.id)[concept.slug]
        assert view.score > 0.3
        assert view.attempts == 1

    def test_repeated_success_approaches_mastery(self, session, user, concept):
        service = MasteryService(session)
        for _ in range(8):
            service.record(user, [concept.slug], Evidence(raw_score=1.0))
        view = service.view_by_slug(user.id)[concept.slug]
        assert view.score >= MASTERY_THRESHOLD
        assert view.is_mastered

    def test_unaided_beats_hinted_over_the_same_attempts(self, session, user, concept):
        from app.models import User
        from app.services.auth import AuthService

        other: User = AuthService(session).register(
            email="other@example.com",
            password="another-strong-password-1",
            display_name="Other",
        )
        service = MasteryService(session)
        for _ in range(5):
            service.record(user, [concept.slug], Evidence(raw_score=1.0))
            service.record(other, [concept.slug], Evidence(raw_score=1.0, hints_used=3))
        unaided = service.view_by_slug(user.id)[concept.slug].score
        hinted = service.view_by_slug(other.id)[concept.slug].score
        assert unaided > hinted

    def test_failure_reduces_the_score(self, session, user, concept):
        service = MasteryService(session)
        for _ in range(5):
            service.record(user, [concept.slug], Evidence(raw_score=1.0))
        before = service.view_by_slug(user.id)[concept.slug].score
        for _ in range(3):
            service.record(user, [concept.slug], Evidence(raw_score=0.0))
        after = service.view_by_slug(user.id)[concept.slug].score
        assert after < before

    def test_mastery_can_be_lost(self, session, user, concept):
        service = MasteryService(session)
        for _ in range(8):
            service.record(user, [concept.slug], Evidence(raw_score=1.0))
        assert service.view_by_slug(user.id)[concept.slug].is_mastered
        for _ in range(6):
            service.record(user, [concept.slug], Evidence(raw_score=0.0))
        assert not service.view_by_slug(user.id)[concept.slug].is_mastered

    def test_misconceptions_are_tallied(self, session, user, concept):
        service = MasteryService(session)
        service.record(user, [concept.slug], Evidence(raw_score=0.0), misconceptions=["off-by-one"])
        service.record(user, [concept.slug], Evidence(raw_score=0.0), misconceptions=["off-by-one"])
        record = session.query(ConceptMastery).filter_by(user_id=user.id).one()
        assert record.misconception_counts["off-by-one"] == 2
        assert "off-by-one" in service.view_by_slug(user.id)[concept.slug].top_misconceptions

    def test_decay_applies_on_read(self, session, user, concept):
        service = MasteryService(session)
        for _ in range(8):
            service.record(user, [concept.slug], Evidence(raw_score=1.0))
        record = session.query(ConceptMastery).filter_by(user_id=user.id).one()
        stored = record.score

        record.last_practiced_at = datetime.now(UTC) - timedelta(days=60)
        record.confidence = 0.3
        session.flush()

        assert service.view_by_slug(user.id)[concept.slug].score < stored

    def test_overall_mastery_counts_untouched_concepts_as_zero(self, session, user, concept):
        session.add(
            Concept(
                slug="untouched",
                name="Untouched",
                description="",
                category="fundamentals",
                weight=1.0,
            )
        )
        session.flush()
        service = MasteryService(session)
        for _ in range(8):
            service.record(user, [concept.slug], Evidence(raw_score=1.0))
        overall = service.overall_mastery(user.id)
        assert 0.4 < overall < 0.6

    def test_weak_concepts_are_ordered_lowest_first(self, session, user):
        for slug, _score in (("easy", 1.0), ("hard", 0.0)):
            session.add(Concept(slug=slug, name=slug, description="", category="fundamentals"))
        session.flush()
        service = MasteryService(session)
        for _ in range(4):
            service.record(user, ["easy"], Evidence(raw_score=1.0))
            service.record(user, ["hard"], Evidence(raw_score=0.0))
        weak = service.weak_concepts(user.id)
        assert weak[0].concept_slug == "hard"

    def test_unknown_concept_slug_is_ignored(self, session, user):
        service = MasteryService(session)
        assert service.record(user, ["does-not-exist"], Evidence(raw_score=1.0)) == []
