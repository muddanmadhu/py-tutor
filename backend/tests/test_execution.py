"""Tests for the sandboxed execution engine.

The security properties are the point of these tests: the sandbox must stop
infinite loops, bound output, refuse path escapes and clean up after itself.
"""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.errors import ValidationFailure
from app.execution.base import ExecutionJob, build_job
from app.models.enums import ExecutionMode


class TestJobValidation:
    def test_rejects_empty_file_set(self):
        with pytest.raises(ValidationFailure):
            build_job(get_settings(), files={})

    def test_rejects_absolute_path(self):
        with pytest.raises(ValidationFailure, match="relative"):
            build_job(get_settings(), files={"/etc/passwd": "x"}, entrypoint="/etc/passwd")

    def test_rejects_parent_traversal(self):
        with pytest.raises(ValidationFailure, match="relative"):
            build_job(get_settings(), files={"../escape.py": "x"}, entrypoint="../escape.py")

    def test_rejects_disallowed_extension(self):
        with pytest.raises(ValidationFailure, match="not permitted"):
            build_job(get_settings(), files={"payload.sh": "rm -rf /"})

    def test_rejects_missing_entrypoint(self):
        with pytest.raises(ValidationFailure, match="not among"):
            build_job(get_settings(), files={"other.py": "x"}, entrypoint="main.py")

    def test_rejects_too_many_files(self):
        settings = get_settings()
        files = {f"f{i}.py": "" for i in range(settings.exec_max_files + 5)}
        files["main.py"] = ""
        with pytest.raises(ValidationFailure, match="At most"):
            build_job(settings, files=files)

    def test_rejects_oversized_source(self):
        settings = get_settings()
        payload = "x" * (settings.exec_max_source_bytes + 1)
        with pytest.raises(ValidationFailure, match="source size"):
            build_job(settings, files={"main.py": payload})

    def test_clamps_timeout_to_the_configured_maximum(self):
        settings = get_settings()
        job = build_job(settings, files={"main.py": "pass"}, timeout_seconds=10_000)
        assert job.timeout_seconds <= settings.exec_timeout_seconds

    def test_accepts_nested_relative_paths(self):
        job = build_job(
            get_settings(),
            files={"main.py": "import pkg.util", "pkg/util.py": "x = 1"},
        )
        assert "pkg/util.py" in job.files


class TestExecution:
    def test_runs_a_hello_world(self, executor):
        result = executor.run(ExecutionJob(files={"main.py": "print('hello')"}))
        assert result.ok
        assert result.exit_code == 0
        assert result.stdout.strip() == "hello"

    def test_captures_stderr_and_exit_code(self, executor):
        result = executor.run(ExecutionJob(files={"main.py": "raise ValueError('boom')"}))
        assert not result.ok
        assert result.exit_code != 0
        assert "ValueError: boom" in result.stderr

    def test_reads_stdin(self, executor):
        result = executor.run(
            ExecutionJob(
                files={"main.py": "print(input().upper())"},
                stdin="quiet\n",
            )
        )
        assert result.stdout.strip() == "QUIET"

    def test_supports_multiple_files(self, executor):
        result = executor.run(
            ExecutionJob(
                files={
                    "main.py": "from helper import shout\nprint(shout('hi'))",
                    "helper.py": "def shout(text):\n    return text.upper() + '!'",
                }
            )
        )
        assert result.stdout.strip() == "HI!"

    def test_infinite_loop_is_stopped(self, executor):
        result = executor.run(
            ExecutionJob(files={"main.py": "while True:\n    pass"}, timeout_seconds=2)
        )
        assert result.timed_out
        assert not result.ok
        assert "time limit" in result.stderr

    def test_output_is_truncated(self, executor):
        result = executor.run(
            ExecutionJob(
                files={"main.py": "print('x' * 500_000)"},
                timeout_seconds=8,
            )
        )
        assert result.stdout_truncated
        assert len(result.stdout) < 500_000

    def test_runs_pytest_and_reports_failures(self, executor):
        result = executor.run(
            ExecutionJob(
                files={
                    "main.py": "def add(a, b):\n    return a - b\n",
                    "test_main.py": (
                        "from main import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n"
                    ),
                },
                mode=ExecutionMode.PYTEST,
                pytest_args=("-v", "--color=no", "-p", "no:cacheprovider"),
                timeout_seconds=25,
            )
        )
        assert not result.ok
        assert "test_add" in result.stdout

    def test_runs_pytest_and_reports_success(self, executor):
        result = executor.run(
            ExecutionJob(
                files={
                    "main.py": "def add(a, b):\n    return a + b\n",
                    "test_main.py": (
                        "from main import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n"
                    ),
                },
                mode=ExecutionMode.PYTEST,
                pytest_args=("-v", "--color=no", "-p", "no:cacheprovider"),
                timeout_seconds=25,
            )
        )
        assert result.ok
        assert "PASSED" in result.stdout

    def test_workspace_does_not_persist_between_runs(self, executor):
        first = executor.run(
            ExecutionJob(files={"main.py": "open('leak.txt', 'w').write('data')\nprint('wrote')"})
        )
        assert first.ok
        second = executor.run(
            ExecutionJob(files={"main.py": "import os\nprint('leak.txt' in os.listdir('.'))"})
        )
        assert second.stdout.strip() == "False"

    def test_reports_syntax_errors_without_crashing_the_engine(self, executor):
        result = executor.run(ExecutionJob(files={"main.py": "def broken(:"}))
        assert not result.ok
        assert "SyntaxError" in result.stderr

    def test_healthy(self, executor):
        assert executor.healthy() is True


class TestRateLimiter:
    def test_allows_up_to_the_limit_then_raises(self):
        from app.core.errors import RateLimitError
        from app.execution.factory import ExecutionRateLimiter

        limiter = ExecutionRateLimiter(limit_per_minute=3)
        for _ in range(3):
            limiter.check("user-1")
        with pytest.raises(RateLimitError):
            limiter.check("user-1")

    def test_limits_are_per_user(self):
        from app.execution.factory import ExecutionRateLimiter

        limiter = ExecutionRateLimiter(limit_per_minute=1)
        limiter.check("user-1")
        limiter.check("user-2")  # must not raise
