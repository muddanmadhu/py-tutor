"""API integration tests.

These exercise the HTTP surface end to end: register, authenticate, read a
lesson, run code in the sandbox, submit an exercise, watch mastery move, use the
hint ladder, search, and get a code review. They are the executable form of the
Definition of Done in the README.
"""

from __future__ import annotations

import pytest


class TestHealth:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ready_reports_checks(self, client):
        body = client.get("/ready").json()
        assert "checks" in body
        assert body["checks"]["database"] is True

    def test_openapi_is_served(self, client):
        assert client.get("/openapi.json").status_code == 200

    def test_correlation_id_is_echoed(self, client):
        response = client.get("/health", headers={"X-Correlation-ID": "abc123"})
        assert response.headers["X-Correlation-ID"] == "abc123"

    def test_security_headers_present(self, client):
        headers = client.get("/health").headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"


class TestAuth:
    def test_register_and_login(self, client):
        payload = {
            "email": "new@example.com",
            "password": "a-strong-test-password-1",
            "display_name": "New Learner",
        }
        created = client.post("/api/auth/register", json=payload)
        assert created.status_code == 201
        assert created.json()["user"]["email"] == "new@example.com"

        logged_in = client.post(
            "/api/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        assert logged_in.status_code == 200
        assert logged_in.json()["tokens"]["access_token"]

    def test_duplicate_email_conflicts(self, client):
        payload = {
            "email": "dupe@example.com",
            "password": "a-strong-test-password-1",
            "display_name": "Dupe",
        }
        assert client.post("/api/auth/register", json=payload).status_code == 201
        conflict = client.post("/api/auth/register", json=payload)
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "conflict"

    def test_weak_password_is_rejected(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "weak@example.com", "password": "password", "display_name": "W"},
        )
        assert response.status_code == 422

    def test_wrong_password_is_indistinguishable_from_unknown_email(self, client, user):
        unknown = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "a-strong-test-password-1"},
        )
        wrong = client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong-password-entirely"},
        )
        assert unknown.status_code == wrong.status_code == 401
        assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]

    def test_me_requires_a_token(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_rejects_a_garbage_token(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer nonsense"})
        assert response.status_code == 401

    def test_me_returns_the_profile(self, client, auth_headers):
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "learner@example.com"

    def test_refresh_issues_new_tokens(self, client, user):
        from app.services.auth import AuthService

        tokens = AuthService.issue_tokens(user)
        response = client.post("/api/auth/refresh", json={"refresh_token": tokens.refresh_token})
        assert response.status_code == 200
        assert response.json()["access_token"]

    def test_access_token_is_not_accepted_as_a_refresh_token(self, client, user):
        from app.services.auth import AuthService

        tokens = AuthService.issue_tokens(user)
        response = client.post("/api/auth/refresh", json={"refresh_token": tokens.access_token})
        assert response.status_code == 401

    def test_profile_update(self, client, auth_headers):
        response = client.patch(
            "/api/auth/me",
            json={"display_name": "Renamed", "goal": "Ship a service"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Renamed"


class TestCurriculum:
    def test_lists_courses(self, seeded_client):
        response = seeded_client.get("/api/courses")
        assert response.status_code == 200
        courses = response.json()
        assert courses
        assert courses[0]["lesson_count"] > 0

    def test_course_detail_includes_the_module_tree(self, seeded_client):
        response = seeded_client.get("/api/courses/python-engineering-mastery")
        assert response.status_code == 200
        body = response.json()
        assert body["modules"]
        assert body["modules"][0]["lessons"]

    def test_unknown_course_is_404_with_the_error_envelope(self, seeded_client):
        response = seeded_client.get("/api/courses/does-not-exist")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "course_not_found"

    def test_lesson_detail_has_content_and_navigation(self, seeded_client):
        response = seeded_client.get("/api/lessons/python-fundamentals")
        assert response.status_code == 200
        lesson = response.json()
        assert lesson["body"]
        assert lesson["exercises"]
        assert lesson["next_lesson_slug"]

    def test_every_lesson_answers_the_required_questions(self, seeded_client):
        """Spec §49 is enforced as data, so this is checkable."""
        from app.content.schema import REQUIRED_SECTIONS

        course = seeded_client.get("/api/courses/python-engineering-mastery").json()
        for module in course["modules"]:
            for summary in module["lessons"]:
                lesson = seeded_client.get(f"/api/lessons/{summary['slug']}").json()
                missing = [key for key in REQUIRED_SECTIONS if not lesson["sections"].get(key)]
                assert not missing, f"{summary['slug']} is missing {missing}"

    def test_concepts_expose_their_prerequisites(self, seeded_client):
        concepts = seeded_client.get("/api/concepts").json()
        by_slug = {c["slug"]: c for c in concepts}
        assert "loops" in by_slug
        assert "conditionals" in by_slug["loops"]["prerequisites"]

    def test_view_and_progress(self, seeded_client, auth_headers):
        response = seeded_client.post("/api/lessons/python-fundamentals/view", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_lesson_with_exercises_cannot_be_completed_by_clicking_next(
        self, seeded_client, auth_headers
    ):
        seeded_client.post("/api/lessons/python-fundamentals/view", headers=auth_headers)
        response = seeded_client.post(
            "/api/lessons/python-fundamentals/complete", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"


class TestExecution:
    def test_runs_code(self, client, auth_headers):
        response = client.post(
            "/api/execution/run",
            json={"files": {"main.py": "print(2 + 2)"}, "entrypoint": "main.py"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["stdout"].strip() == "4"

    def test_explains_a_runtime_error(self, client, auth_headers):
        response = client.post(
            "/api/execution/run",
            json={"files": {"main.py": "print(undefined_name)"}},
            headers=auth_headers,
        )
        body = response.json()
        assert body["ok"] is False
        assert body["error_explanation"]
        assert "NameError" in body["error_explanation"]

    def test_rejects_a_path_escape(self, client, auth_headers):
        response = client.post(
            "/api/execution/run",
            json={"files": {"../../etc/passwd": "x"}, "entrypoint": "../../etc/passwd"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_requires_authentication(self, client):
        response = client.post("/api/execution/run", json={"files": {"main.py": "print(1)"}})
        assert response.status_code == 401

    def test_health_reports_the_backend(self, client, auth_headers):
        body = client.get("/api/execution/health", headers=auth_headers).json()
        assert body["backend"] in {"docker", "subprocess"}
        assert "isolated" in body

    def test_snippets_round_trip(self, client, auth_headers):
        saved = client.put(
            "/api/execution/snippets/scratch",
            json={"files": {"main.py": "print(1)"}, "entrypoint": "main.py"},
            headers=auth_headers,
        )
        assert saved.status_code == 200
        listed = client.get("/api/execution/snippets", headers=auth_headers).json()
        assert listed[0]["name"] == "scratch"
        assert (
            client.delete("/api/execution/snippets/scratch", headers=auth_headers).status_code
            == 200
        )


class TestSubmissionFlow:
    """The core loop: attempt, hint, submit, master."""

    def test_exercise_detail_hides_the_hidden_tests(self, seeded_client, auth_headers):
        response = seeded_client.get("/api/exercises/functions-stats", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "hidden_files" not in body
        assert "solution_files" not in body
        assert body["hint_count"] == 4

    def test_correct_submission_passes_and_moves_mastery(self, seeded_client, auth_headers):
        solution = 'print("Hello, PyForge")\n'
        response = seeded_client.post(
            "/api/exercises/fundamentals-hello/submit",
            json={"files": {"main.py": solution}, "time_spent_seconds": 45},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "passed"
        assert body["score"] == 1.0
        assert body["xp_awarded"] > 0
        assert body["mastery_deltas"]
        assert body["mastery_deltas"][0]["delta"] > 0

    def test_incorrect_submission_fails_with_a_diff(self, seeded_client, auth_headers):
        response = seeded_client.post(
            "/api/exercises/fundamentals-hello/submit",
            json={"files": {"main.py": 'print("wrong")'}},
            headers=auth_headers,
        )
        body = response.json()
        assert body["status"] == "failed"
        assert body["checks"][0]["diff"]

    def test_pytest_graded_exercise(self, seeded_client, auth_headers):
        solution = (
            "def fizzbuzz(n: int) -> list[str]:\n"
            "    out = []\n"
            "    for i in range(1, n + 1):\n"
            "        if i % 15 == 0:\n"
            "            out.append('FizzBuzz')\n"
            "        elif i % 3 == 0:\n"
            "            out.append('Fizz')\n"
            "        elif i % 5 == 0:\n"
            "            out.append('Buzz')\n"
            "        else:\n"
            "            out.append(str(i))\n"
            "    return out\n"
        )
        response = seeded_client.post(
            "/api/exercises/loops-fizzbuzz/submit",
            json={"files": {"main.py": solution}},
            headers=auth_headers,
        )
        body = response.json()
        assert body["status"] == "passed", body["feedback"]
        assert len(body["checks"]) >= 5

    def test_hints_unlock_in_order(self, seeded_client, auth_headers):
        skipping = seeded_client.post("/api/exercises/loops-fizzbuzz/hints/3", headers=auth_headers)
        assert skipping.status_code == 422

        first = seeded_client.post("/api/exercises/loops-fizzbuzz/hints/1", headers=auth_headers)
        assert first.status_code == 200
        assert first.json()["text"]

        second = seeded_client.post("/api/exercises/loops-fizzbuzz/hints/2", headers=auth_headers)
        assert second.status_code == 200

    def test_solution_is_gated_behind_effort(self, seeded_client, auth_headers):
        blocked = seeded_client.post("/api/exercises/loops-fizzbuzz/solution", headers=auth_headers)
        assert blocked.status_code == 422
        assert "attempts" in blocked.json()["error"]["details"]

        for _ in range(3):
            seeded_client.post(
                "/api/exercises/loops-fizzbuzz/submit",
                json={"files": {"main.py": "def fizzbuzz(n):\n    return []"}},
                headers=auth_headers,
            )
        unlocked = seeded_client.post(
            "/api/exercises/loops-fizzbuzz/solution", headers=auth_headers
        )
        assert unlocked.status_code == 200
        assert unlocked.json()["files"]

    def test_submission_history_is_kept(self, seeded_client, auth_headers):
        for _ in range(2):
            seeded_client.post(
                "/api/exercises/fundamentals-hello/submit",
                json={"files": {"main.py": 'print("nope")'}},
                headers=auth_headers,
            )
        history = seeded_client.get(
            "/api/exercises/fundamentals-hello/submissions", headers=auth_headers
        ).json()
        assert len(history) == 2
        assert history[0]["attempt_number"] == 2

    def test_remediation_appears_after_repeated_failure(self, seeded_client, auth_headers):
        assert (
            seeded_client.get(
                "/api/exercises/loops-fizzbuzz/remediation", headers=auth_headers
            ).json()
            is None
        )
        for _ in range(3):
            seeded_client.post(
                "/api/exercises/loops-fizzbuzz/submit",
                json={"files": {"main.py": "def fizzbuzz(n):\n    return []"}},
                headers=auth_headers,
            )
        plan = seeded_client.get(
            "/api/exercises/loops-fizzbuzz/remediation", headers=auth_headers
        ).json()
        assert plan is not None
        assert plan["message"]

    def test_multiple_choice_submission(self, seeded_client, auth_headers):
        response = seeded_client.post(
            "/api/exercises/variables-aliasing-quiz/submit",
            json={"files": {}, "selected_index": 1},
            headers=auth_headers,
        )
        assert response.json()["status"] == "passed"

    def test_wrong_multiple_choice_records_a_misconception(self, seeded_client, auth_headers):
        seeded_client.post(
            "/api/exercises/variables-aliasing-quiz/submit",
            json={"files": {}, "selected_index": 0},
            headers=auth_headers,
        )
        mastery = seeded_client.get("/api/mastery", headers=auth_headers).json()
        misconceptions = [m for c in mastery["concepts"] for m in c["top_misconceptions"]]
        assert "aliasing" in misconceptions


class TestProgress:
    def test_dashboard_shape(self, seeded_client, auth_headers):
        response = seeded_client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        for key in (
            "overall_mastery",
            "level",
            "streak",
            "counters",
            "weak_areas",
            "recommendations",
            "achievements",
            "certifications",
            "activity_series",
        ):
            assert key in body

    def test_recommendations_are_returned_for_a_new_learner(self, seeded_client, auth_headers):
        recommendations = seeded_client.get("/api/recommendations", headers=auth_headers).json()
        assert recommendations
        assert recommendations[0]["kind"] in {
            "advance",
            "continue",
            "review",
            "remediate",
            "project",
        }

    def test_readiness_map_blocks_on_prerequisites(self, seeded_client, auth_headers):
        readiness = seeded_client.get("/api/mastery/readiness", headers=auth_headers).json()
        by_slug = {item["concept_slug"]: item for item in readiness}
        assert by_slug["variables"]["ready"] is True
        assert by_slug["loops"]["ready"] is False
        assert "conditionals" in by_slug["loops"]["blocked_by"]

    def test_achievements_are_awarded_for_real_work(self, seeded_client, auth_headers):
        seeded_client.post(
            "/api/exercises/fundamentals-hello/submit",
            json={"files": {"main.py": 'print("Hello, PyForge")'}},
            headers=auth_headers,
        )
        achievements = seeded_client.get("/api/achievements", headers=auth_headers).json()
        earned = [a["slug"] for a in achievements if a["earned"]]
        assert "first-steps" in earned

    def test_certifications_start_locked_with_reasons(self, seeded_client, auth_headers):
        certifications = seeded_client.get("/api/certifications", headers=auth_headers).json()
        foundations = next(c for c in certifications if c["level"] == "python_foundations")
        assert foundations["earned"] is False
        assert foundations["unmet_requirements"]

    def test_claiming_an_unearned_certification_is_refused(self, seeded_client, auth_headers):
        response = seeded_client.post(
            "/api/certifications/python_foundations/claim", headers=auth_headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["details"]["unmet_requirements"]

    def test_course_progress(self, seeded_client, auth_headers):
        body = seeded_client.get(
            "/api/progress/courses/python-engineering-mastery", headers=auth_headers
        ).json()
        assert body["lessons_total"] > 0
        assert body["modules"]


class TestProjects:
    def test_lists_projects_across_the_guidance_spectrum(self, seeded_client, auth_headers):
        projects = seeded_client.get("/api/projects", headers=auth_headers).json()
        guidance = {p["guidance"] for p in projects}
        assert {"fully_guided", "requirements_only", "independent"} <= guidance

    def test_project_detail_creates_a_workspace(self, seeded_client, auth_headers):
        body = seeded_client.get("/api/projects/calculator-cli", headers=auth_headers).json()
        assert body["requirements"]
        assert body["rubric"]
        assert body["workspace"]["files"]

    def test_workspace_autosave(self, seeded_client, auth_headers):
        seeded_client.get("/api/projects/calculator-cli", headers=auth_headers)
        response = seeded_client.put(
            "/api/projects/calculator-cli/workspace",
            json={"files": {"main.py": "print(1)"}, "entrypoint": "main.py"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["files"]["main.py"] == "print(1)"

    def test_capstone_is_requirements_only(self, seeded_client, auth_headers):
        body = seeded_client.get(
            "/api/projects/enterprise-automation-service", headers=auth_headers
        ).json()
        assert body["is_capstone"] is True
        assert body["milestones"] == []
        assert "Requirement document" in body["requirements"]


class TestReferenceAndSearch:
    def test_reference_index(self, seeded_client):
        entries = seeded_client.get("/api/reference").json()
        assert entries
        assert {"key", "signature", "summary"} <= set(entries[0])

    def test_reference_entry_detail(self, seeded_client):
        body = seeded_client.get("/api/reference/list.append").json()
        assert body["key"] == "list.append"
        assert body["common_mistakes"]
        assert body["performance_notes"]

    def test_search_ranks_the_reference_entry_first_for_an_api_query(self, seeded_client):
        hits = seeded_client.get("/api/search", params={"q": "list.append"}).json()["hits"]
        assert hits
        assert hits[0]["kind"] == "reference"
        assert hits[0]["slug"] == "list.append"

    def test_natural_language_search_finds_the_right_material(self, seeded_client):
        body = seeded_client.get(
            "/api/search", params={"q": "How do I handle a timeout in requests?"}
        ).json()
        slugs = {hit["slug"] for hit in body["hits"]}
        assert "requests.get" in slugs or "apis-and-http" in slugs

    def test_search_can_be_filtered_by_kind(self, seeded_client):
        body = seeded_client.get("/api/search", params={"q": "loops", "kinds": "lesson"}).json()
        assert all(hit["kind"] == "lesson" for hit in body["hits"])

    def test_search_with_no_matches_is_empty_not_an_error(self, seeded_client):
        body = seeded_client.get("/api/search", params={"q": "zzzzqqq"}).json()
        assert body["hits"] == []


class TestCodeReview:
    def test_reviews_submitted_code(self, client, auth_headers):
        response = client.post(
            "/api/code-review",
            json={"files": {"main.py": "def f(x, acc=[]):\n    return eval(x)"}},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["findings"]
        assert body["overall_score"] < 1.0
        assert body["summary"]

    def test_requires_authentication(self, client):
        assert client.post("/api/code-review", json={"files": {}}).status_code == 401


class TestAITutor:
    def test_status_reports_the_offline_backend(self, client, auth_headers):
        body = client.get("/api/ai/status", headers=auth_headers).json()
        assert body["live"] is False
        assert body["backend"] == "offline"

    def test_conversation_round_trip(self, client, auth_headers):
        created = client.post(
            "/api/ai/conversations",
            json={"mode": "explain_error"},
            headers=auth_headers,
        )
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        reply = client.post(
            f"/api/ai/conversations/{conversation_id}/messages",
            json={
                "message": "What does this mean?",
                "error_output": "NameError: name 'total' is not defined",
            },
            headers=auth_headers,
        )
        assert reply.status_code == 200
        assert "NameError" in reply.json()["content"]

    def test_tutor_withholds_the_solution_while_practising(self, seeded_client, auth_headers):
        created = seeded_client.post(
            "/api/ai/conversations",
            json={"mode": "hint", "exercise_slug": "loops-fizzbuzz"},
            headers=auth_headers,
        ).json()
        reply = seeded_client.post(
            f"/api/ai/conversations/{created['id']}/messages",
            json={"message": "Just give me the full answer please"},
            headers=auth_headers,
        ).json()
        assert reply["meta"]["withheld_solution"] is True

    def test_cannot_read_another_learners_conversation(self, client, auth_headers, session):
        from app.services.auth import AuthService

        other = AuthService(session).register(
            email="intruder@example.com",
            password="another-strong-password-1",
            display_name="Intruder",
        )
        session.commit()
        intruder_headers = {
            "Authorization": f"Bearer {AuthService.issue_tokens(other).access_token}"
        }
        created = client.post(
            "/api/ai/conversations", json={"mode": "freeform"}, headers=auth_headers
        ).json()
        response = client.get(f"/api/ai/conversations/{created['id']}", headers=intruder_headers)
        assert response.status_code == 404


class TestInterview:
    def test_question_bank_hides_the_answers(self, seeded_client):
        questions = seeded_client.get("/api/interview/questions").json()
        assert questions
        assert "correct_index" not in questions[0]

    def test_filter_by_track(self, seeded_client):
        questions = seeded_client.get("/api/interview/questions", params={"track": "sdet"}).json()
        assert all("sdet" in q["tracks"] for q in questions)

    def test_answering_reveals_the_explanation(self, seeded_client, auth_headers):
        response = seeded_client.post(
            "/api/interview/answer",
            json={"slug": "iq-mutable-default", "selected_index": 1},
            headers=auth_headers,
        )
        body = response.json()
        assert body["correct"] is True
        assert body["explanation"]


class TestAnalytics:
    def test_personal_analytics(self, seeded_client, auth_headers):
        body = seeded_client.get("/api/analytics/me", headers=auth_headers).json()
        assert "summary" in body
        assert len(body["activity_series"]) == 60

    def test_platform_analytics_requires_an_author(self, seeded_client, auth_headers):
        assert seeded_client.get("/api/analytics/platform", headers=auth_headers).status_code == 403


class TestErrorEnvelope:
    def test_validation_errors_use_the_envelope(self, client):
        response = client.post("/api/auth/register", json={"email": "not-an-email"})
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "invalid_request"
        assert error["details"]["fields"]

    def test_404_uses_the_envelope(self, client):
        response = client.get("/api/nope")
        assert response.status_code == 404
        assert "error" in response.json()

    @pytest.mark.parametrize("path", ["/api/dashboard", "/api/mastery", "/api/projects"])
    def test_protected_endpoints_require_a_token(self, client, path):
        assert client.get(path).status_code == 401
