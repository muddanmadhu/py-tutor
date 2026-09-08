"""Client-side execution: grading from a result the browser reported.

On a GitHub Pages deployment there is no server-side sandbox — learner code
runs in the visitor's browser under Pyodide and the output is posted back. These
tests pin the two halves of that contract: the server must grade from what it is
given, and it must not hand out the recipe (or trust the report) when it has a
sandbox of its own.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import ExecutorKind, get_settings
from app.db.session import get_db
from app.execution.factory import ClientExecutor, get_executor, get_rate_limiter
from app.main import create_app
from app.models.enums import SubmissionStatus


@pytest.fixture()
def client_mode() -> Iterator[None]:
    """Run the application as a deployment with no server-side sandbox."""
    os.environ["PYFORGE_EXECUTOR"] = "client"
    get_settings.cache_clear()
    get_executor.cache_clear()
    yield
    os.environ["PYFORGE_EXECUTOR"] = "subprocess"
    get_settings.cache_clear()
    get_executor.cache_clear()


@pytest.fixture()
def client_mode_client(client_mode: None, seeded_session: Session) -> Iterator[TestClient]:
    """An API client for a client-executed deployment."""
    app = create_app()

    def _override_db() -> Iterator[Session]:
        yield seeded_session

    app.dependency_overrides[get_db] = _override_db
    get_rate_limiter().reset()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _stdout_exercise(session: Session) -> str:
    """Slug of a seeded exercise graded on its printed output."""
    from sqlalchemy import select

    from app.models import Exercise

    slug = session.scalar(select(Exercise.slug).where(Exercise.grader == "stdout_match"))
    assert slug, "the seed curriculum should contain a stdout_match exercise"
    return str(slug)


class TestExecutionPlan:
    """What the client is told about how to run an exercise."""

    def test_plan_is_absent_when_the_server_has_a_sandbox(
        self, seeded_client: TestClient, auth_headers: dict[str, str], seeded_session: Session
    ) -> None:
        slug = _stdout_exercise(seeded_session)
        response = seeded_client.get(f"/api/exercises/{slug}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["execution_plan"] is None

    def test_plan_is_present_when_the_client_must_execute(
        self,
        client_mode_client: TestClient,
        auth_headers: dict[str, str],
        seeded_session: Session,
    ) -> None:
        slug = _stdout_exercise(seeded_session)
        response = client_mode_client.get(f"/api/exercises/{slug}", headers=auth_headers)
        assert response.status_code == 200
        plan = response.json()["execution_plan"]
        assert plan is not None
        assert plan["mode"] == "script"
        assert plan["entrypoint"].endswith(".py")


class TestClientReportedGrading:
    """Grading a submission from output the client produced."""

    def test_reported_success_passes(
        self,
        client_mode_client: TestClient,
        auth_headers: dict[str, str],
        seeded_session: Session,
    ) -> None:
        from sqlalchemy import select

        from app.models import Exercise

        exercise = seeded_session.scalar(select(Exercise).where(Exercise.grader == "stdout_match"))
        assert exercise is not None
        expected = exercise.grader_config["expected_stdout"]

        response = client_mode_client.post(
            f"/api/exercises/{exercise.slug}/submit",
            headers=auth_headers,
            json={
                "files": {"main.py": "print('whatever')"},
                "execution": {"exit_code": 0, "stdout": expected, "duration_ms": 12},
            },
        )
        assert response.status_code == 200
        body = response.json()
        # The server graded the *reported* output, not the submitted source —
        # that is the whole point of the client-execution mode.
        assert body["status"] == SubmissionStatus.PASSED.value
        assert body["score"] == 1.0

    def test_reported_mismatch_fails_with_a_diff(
        self,
        client_mode_client: TestClient,
        auth_headers: dict[str, str],
        seeded_session: Session,
    ) -> None:
        slug = _stdout_exercise(seeded_session)
        response = client_mode_client.post(
            f"/api/exercises/{slug}/submit",
            headers=auth_headers,
            json={
                "files": {"main.py": "print('nope')"},
                "execution": {"exit_code": 0, "stdout": "definitely not it", "duration_ms": 5},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == SubmissionStatus.FAILED.value
        assert body["checks"][0]["diff"]

    def test_a_missing_report_is_an_error_not_a_pass(
        self,
        client_mode_client: TestClient,
        auth_headers: dict[str, str],
        seeded_session: Session,
    ) -> None:
        """Failing closed matters: a silent pass would let anyone skip the work."""
        slug = _stdout_exercise(seeded_session)
        response = client_mode_client.post(
            f"/api/exercises/{slug}/submit",
            headers=auth_headers,
            json={"files": {"main.py": "print('x')"}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == SubmissionStatus.ERROR.value
        assert body["score"] == 0.0

    def test_reported_timeout_is_graded_as_a_timeout(
        self,
        client_mode_client: TestClient,
        auth_headers: dict[str, str],
        seeded_session: Session,
    ) -> None:
        slug = _stdout_exercise(seeded_session)
        response = client_mode_client.post(
            f"/api/exercises/{slug}/submit",
            headers=auth_headers,
            json={
                "files": {"main.py": "while True: pass"},
                "execution": {"exit_code": -1, "timed_out": True, "duration_ms": 10_000},
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == SubmissionStatus.TIMED_OUT.value

    def test_a_report_is_ignored_when_the_server_can_execute(
        self, seeded_client: TestClient, auth_headers: dict[str, str], seeded_session: Session
    ) -> None:
        """A forged pass must not work against a deployment with a real sandbox."""
        from sqlalchemy import select

        from app.models import Exercise

        exercise = seeded_session.scalar(select(Exercise).where(Exercise.grader == "stdout_match"))
        assert exercise is not None

        response = seeded_client.post(
            f"/api/exercises/{exercise.slug}/submit",
            headers=auth_headers,
            json={
                "files": {"main.py": "print('wrong')"},
                "execution": {
                    "exit_code": 0,
                    "stdout": exercise.grader_config["expected_stdout"],
                    "duration_ms": 1,
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] != SubmissionStatus.PASSED.value


class TestClientExecutor:
    """The placeholder backend used when execution is the client's job."""

    def test_it_is_selected_in_client_mode(self, client_mode: None) -> None:
        assert get_settings().executor is ExecutorKind.CLIENT
        assert isinstance(get_executor(), ClientExecutor)

    def test_it_reports_healthy(self, client_mode: None) -> None:
        assert get_executor().healthy() is True

    def test_running_through_it_fails_rather_than_silently_succeeding(
        self, client_mode: None
    ) -> None:
        from app.execution.base import build_job

        job = build_job(get_settings(), files={"main.py": "print(1)"})
        result = get_executor().run(job)
        assert result.ok is False
        assert result.error


class TestProductionInvariants:
    """Which executors a production deployment is allowed to boot with."""

    @staticmethod
    def _settings(**overrides: object) -> object:
        from app.core.config import Settings

        base: dict[str, object] = {
            "env": "production",
            "debug": False,
            "secret_key": "a-unique-production-secret-key-of-sufficient-length",
            "database_url": "postgresql+psycopg://user:pw@host/db",
            "cors_origins": ["https://example.github.io"],
        }
        base.update(overrides)
        return Settings(**base)  # type: ignore[arg-type]

    def test_client_execution_is_allowed_in_production(self) -> None:
        """Cloud Run cannot run Docker, and it does not need to."""
        settings = self._settings(executor="client")
        assert settings.executor is ExecutorKind.CLIENT  # type: ignore[attr-defined]

    def test_docker_is_allowed_in_production(self) -> None:
        settings = self._settings(executor="docker")
        assert settings.executor is ExecutorKind.DOCKER  # type: ignore[attr-defined]

    def test_subprocess_is_still_refused_in_production(self) -> None:
        """The dev executor shares a process with the API's own secrets."""
        with pytest.raises(ValueError, match="subprocess is dev-only"):
            self._settings(executor="subprocess")

    def test_sqlite_is_still_refused_in_production(self) -> None:
        with pytest.raises(ValueError, match="SQLite"):
            self._settings(executor="client", database_url="sqlite+pysqlite:///./x.db")

    def test_wildcard_cors_is_still_refused_in_production(self) -> None:
        with pytest.raises(ValueError, match="wildcard"):
            self._settings(executor="client", cors_origins=["*"])
