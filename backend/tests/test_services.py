"""Tests for the remaining domain services: auth, adaptive, gamification,
certification, search and the AI tutor's hint policy."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.core.errors import AuthenticationError, ConflictError, ValidationFailure
from app.core.security import (
    TokenError,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.enums import AIMode, CertificationLevel
from app.services.adaptive import AdaptiveService, RecommendationKind
from app.services.ai_tutor import (
    MAX_HINT_LEVEL,
    OfflineTutor,
    TutorContext,
    build_system_prompt,
)
from app.services.auth import AuthService
from app.services.certification import CertificationService
from app.services.gamification import level_for_xp, touch_streak
from app.services.mastery import Evidence, MasteryService
from app.services.search import SearchService, tokenize


class TestPasswordHashing:
    def test_round_trip(self):
        stored = hash_password("a-strong-password-1")
        assert verify_password("a-strong-password-1", stored)

    def test_wrong_password_fails(self):
        assert not verify_password("wrong", hash_password("a-strong-password-1"))

    def test_salt_makes_hashes_unique(self):
        assert hash_password("same") != hash_password("same")

    def test_malformed_hash_returns_false_rather_than_raising(self):
        assert not verify_password("x", "not-a-real-hash")
        assert not verify_password("x", "")

    def test_current_parameters_do_not_need_a_rehash(self):
        assert not needs_rehash(hash_password("a-strong-password-1"))

    def test_weaker_parameters_are_flagged_for_rehash(self):
        stored = hash_password("a-strong-password-1")
        algorithm, _, salt, digest = stored.split("$")
        assert needs_rehash(f"{algorithm}$n=1024,r=8,p=1${salt}${digest}")


class TestTokens:
    def test_round_trip(self):
        token = create_token("user-123", TokenType.ACCESS)
        payload = decode_token(token, TokenType.ACCESS)
        assert payload.subject == "user-123"

    def test_type_confusion_is_rejected(self):
        token = create_token("user-123", TokenType.REFRESH)
        with pytest.raises(TokenError, match="access"):
            decode_token(token, TokenType.ACCESS)

    def test_tampered_token_is_rejected(self):
        token = create_token("user-123", TokenType.ACCESS)
        with pytest.raises(TokenError):
            decode_token(token[:-4] + "aaaa", TokenType.ACCESS)

    def test_garbage_is_rejected(self):
        with pytest.raises(TokenError):
            decode_token("not.a.token", TokenType.ACCESS)


class TestAuthService:
    def test_email_is_normalised(self, session):
        user = AuthService(session).register(
            email="  MiXeD@Example.COM ",
            password="a-strong-password-1",
            display_name="Mixed",
        )
        assert user.email == "mixed@example.com"

    def test_duplicate_registration_conflicts(self, session):
        service = AuthService(session)
        service.register(email="dupe@example.com", password="a-strong-password-1", display_name="A")
        with pytest.raises(ConflictError):
            service.register(
                email="dupe@example.com", password="a-strong-password-1", display_name="B"
            )

    def test_weak_password_is_rejected_with_reasons(self, session):
        with pytest.raises(ValidationFailure) as info:
            AuthService(session).register(
                email="weak@example.com", password="short", display_name="W"
            )
        assert info.value.details["problems"]

    def test_authenticate_rejects_a_deactivated_account(self, session, user):
        user.is_active = False
        session.flush()
        with pytest.raises(AuthenticationError):
            AuthService(session).authenticate(user.email, "a-strong-test-password-1")

    def test_change_password(self, session, user):
        service = AuthService(session)
        service.change_password(user, "a-strong-test-password-1", "a-brand-new-password-2")
        assert service.authenticate(user.email, "a-brand-new-password-2")

    def test_change_password_requires_the_current_one(self, session, user):
        with pytest.raises(AuthenticationError):
            AuthService(session).change_password(user, "wrong", "a-brand-new-password-2")


class TestGamification:
    def test_level_one_at_zero_xp(self):
        level = level_for_xp(0)
        assert level.level == 1
        assert level.title == "Newcomer"

    def test_levels_increase_with_xp(self):
        assert level_for_xp(10_000).level > level_for_xp(1_000).level

    def test_progress_is_a_fraction(self):
        assert 0.0 <= level_for_xp(300).progress <= 1.0

    def test_streak_starts_at_one(self, user):
        assert touch_streak(user, today=date(2026, 9, 6)) == 1

    def test_consecutive_days_extend_the_streak(self, user):
        touch_streak(user, today=date(2026, 9, 6))
        assert touch_streak(user, today=date(2026, 9, 7)) == 2

    def test_same_day_does_not_double_count(self, user):
        touch_streak(user, today=date(2026, 9, 6))
        assert touch_streak(user, today=date(2026, 9, 6)) == 1

    def test_a_gap_resets_the_streak(self, user):
        touch_streak(user, today=date(2026, 9, 6))
        touch_streak(user, today=date(2026, 9, 7))
        assert touch_streak(user, today=date(2026, 9, 10)) == 1

    def test_longest_streak_is_remembered(self, user):
        start = date(2026, 9, 1)
        for offset in range(5):
            touch_streak(user, today=start + timedelta(days=offset))
        touch_streak(user, today=start + timedelta(days=20))
        assert user.longest_streak_days == 5
        assert user.streak_days == 1


class TestAdaptive:
    def test_new_learner_is_told_where_to_start(self, seeded_session, user):
        recommendations = AdaptiveService(seeded_session).recommend(user)
        assert recommendations
        assert any(r.kind is RecommendationKind.ADVANCE for r in recommendations)

    def test_readiness_respects_prerequisites(self, seeded_session, user):
        readiness = {
            item["concept_slug"]: item
            for item in AdaptiveService(seeded_session).concept_readiness(user.id)
        }
        assert readiness["variables"]["ready"] is True
        assert readiness["closures"]["ready"] is False

    def test_mastering_a_prerequisite_unlocks_the_next_concept(self, seeded_session, user):
        mastery = MasteryService(seeded_session)
        for _ in range(8):
            mastery.record(user, ["data-types"], Evidence(raw_score=1.0))
        readiness = {
            item["concept_slug"]: item
            for item in AdaptiveService(seeded_session).concept_readiness(user.id)
        }
        assert readiness["operators"]["ready"] is True

    def test_no_remediation_before_repeated_failure(self, seeded_session, user):
        assert AdaptiveService(seeded_session).remediation_plan(user, "loops-fizzbuzz") is None

    def test_remediation_after_repeated_failure(self, seeded_session, user):
        from app.services.submissions import SubmissionService

        service = SubmissionService(seeded_session)
        for _ in range(3):
            service.submit(
                user,
                "loops-fizzbuzz",
                files={"main.py": "def fizzbuzz(n):\n    return []"},
            )
        plan = AdaptiveService(seeded_session).remediation_plan(user, "loops-fizzbuzz")
        assert plan is not None
        assert plan.explanation
        assert plan.message

    def test_remediation_is_resolved_once_passed(self, seeded_session, user):
        from app.services.submissions import SubmissionService

        SubmissionService(seeded_session).submit(
            user,
            "fundamentals-hello",
            files={"main.py": 'print("Hello, PyForge")'},
        )
        plan = AdaptiveService(seeded_session).remediation_plan(user, "fundamentals-hello")
        assert plan is not None
        assert plan.stage.value == "resolved"


class TestCertification:
    def test_nothing_is_earned_at_the_start(self, seeded_session, user):
        statuses = CertificationService(seeded_session).status_for(user)
        assert statuses
        assert all(not status.earned for status in statuses)
        assert all(status.unmet for status in statuses)

    def test_claiming_without_evidence_is_refused(self, seeded_session, user):
        with pytest.raises(ValidationFailure) as info:
            CertificationService(seeded_session).claim(user, CertificationLevel.FOUNDATIONS)
        assert info.value.details["unmet_requirements"]

    def test_progress_reflects_partial_evidence(self, seeded_session, user):
        service = CertificationService(seeded_session)
        before = next(
            s for s in service.status_for(user) if s.level is CertificationLevel.FOUNDATIONS
        )
        mastery = MasteryService(seeded_session)
        for slug in ("variables", "data-types", "operators", "io-basics"):
            for _ in range(8):
                mastery.record(user, [slug], Evidence(raw_score=1.0))
        after = next(
            s for s in service.status_for(user) if s.level is CertificationLevel.FOUNDATIONS
        )
        assert after.progress > before.progress

    def test_certificate_code_is_deterministic(self, seeded_session, user):
        from app.services.certification import _certificate_code

        assert _certificate_code(user.id, "python_foundations") == _certificate_code(
            user.id, "python_foundations"
        )


class TestSearch:
    def test_tokenizer_keeps_dotted_identifiers(self):
        assert "list.append" in tokenize("how do I use list.append?")

    def test_tokenizer_drops_stopwords(self):
        assert "the" not in tokenize("the loops")

    def test_exact_reference_key_ranks_first(self, seeded_session):
        hits = SearchService(seeded_session).search("dict.get")
        assert hits[0].kind == "reference"
        assert hits[0].slug == "dict.get"

    def test_natural_language_query(self, seeded_session):
        hits = SearchService(seeded_session).search("handle timeout in requests")
        assert hits
        assert any("requests" in hit.slug or "api" in hit.slug for hit in hits)

    def test_kind_filter(self, seeded_session):
        hits = SearchService(seeded_session).search("functions", kinds=["lesson"])
        assert all(hit.kind == "lesson" for hit in hits)

    def test_empty_query_returns_nothing(self, seeded_session):
        assert SearchService(seeded_session).search("   ") == []

    def test_results_carry_a_navigable_url(self, seeded_session):
        for hit in SearchService(seeded_session).search("loops"):
            assert hit.url.startswith("/")


class TestAITutorPolicy:
    def test_practising_prompt_forbids_the_solution(self):
        prompt = build_system_prompt(
            AIMode.HINT,
            TutorContext(exercise_slug="x", exercise_solved=False, hint_level=1),
        )
        assert "Do NOT write the solution" in prompt
        assert "hint level 1" in prompt

    def test_solved_prompt_allows_discussion(self):
        prompt = build_system_prompt(
            AIMode.EXPLAIN_CODE,
            TutorContext(exercise_slug="x", exercise_solved=True),
        )
        assert "already solved" in prompt
        assert "Do NOT write the solution" not in prompt

    def test_reference_solution_is_never_placed_in_the_prompt(self):
        prompt = build_system_prompt(
            AIMode.HINT,
            TutorContext(
                exercise_slug="x",
                exercise_solved=False,
                hint_level=4,
                reference_solution="def secret(): return 42",
            ),
        )
        assert "secret" not in prompt

    def test_hint_level_is_capped_in_the_prompt(self):
        prompt = build_system_prompt(AIMode.HINT, TutorContext(exercise_slug="x", hint_level=99))
        assert f"of {MAX_HINT_LEVEL}" in prompt

    def test_offline_tutor_explains_an_error(self):
        reply = OfflineTutor().generate(
            "",
            [{"role": "user", "content": "what is this?"}],
            TutorContext(error_output="NameError: name 'x' is not defined"),
        )
        assert "NameError" in reply.content

    def test_offline_tutor_serves_the_authored_hint_at_the_current_rung(self):
        reply = OfflineTutor().generate(
            "",
            [{"role": "user", "content": "help"}],
            TutorContext(
                exercise_slug="x",
                hint_level=2,
                authored_hints=("first rung", "second rung", "third rung", "fourth rung"),
            ),
        )
        assert "second rung" in reply.content
        assert "third rung" not in reply.content
        assert reply.withheld_solution is True

    def test_offline_tutor_reviews_code_once_the_exercise_is_solved(self):
        reply = OfflineTutor().generate(
            "",
            [{"role": "user", "content": "how is my code?"}],
            TutorContext(code="def f(x, acc=[]):\n    return acc", exercise_solved=True),
        )
        assert "mutable default" in reply.content.lower()
