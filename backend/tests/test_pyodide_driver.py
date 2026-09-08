"""The in-browser execution driver, exercised against the real graders.

The Pyodide driver is Python source embedded in a TypeScript worker
(``frontend/src/execution/worker.ts``). Its output is a *contract with this
package*: :mod:`app.services.grading` parses the stdout, stderr and exit code it
produces, so a change to either side can silently break grading for every
learner on a client-executed deployment.

These tests extract that driver and run it under CPython. That is not the same
interpreter as Pyodide, so it cannot catch WASM-specific problems — but the
driver is plain standard-library Python, and everything the graders depend on
(exit-code convention, traceback shape, pytest verbose output, truncation) is
identical in both. It already caught a ``NameError`` that turned every learner
runtime error into a harness failure.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.services.grading import _PYTEST_CASE, _PYTEST_TALLY, interpret_traceback

#: Mirrors PYTEST_ARGS in app.services.submissions and runner.ts.
PYTEST_ARGS = ["-v", "--tb=short", "--color=no", "-p", "no:cacheprovider"]

WORKER = Path(__file__).resolve().parents[2] / "frontend" / "src" / "execution" / "worker.ts"


def _extract_driver() -> str:
    """Pull the embedded Python driver out of the worker module."""
    source = WORKER.read_text(encoding="utf-8")
    match = re.search(r"const DRIVER = String\.raw`\n(.*?)\n`;", source, re.S)
    assert match, f"could not find the DRIVER template literal in {WORKER}"
    return match.group(1)


@pytest.fixture()
def driver(tmp_path: Path) -> Callable[..., dict[str, Any]]:
    """A callable that runs a job through the extracted driver."""
    if not WORKER.exists():
        pytest.skip(f"frontend worker not present at {WORKER}")

    namespace: dict[str, Any] = {}
    exec(compile(_extract_driver(), "<driver>", "exec"), namespace)  # noqa: S102
    # Pyodide's virtual filesystem has /workspace; a real machine does not, so
    # the driver's workspace is repointed at a temporary directory. It stays
    # constant across calls within a test, which is what lets the isolation
    # tests below prove that the *driver* clears it rather than the fixture.
    namespace["WORKSPACE"] = str(tmp_path / "workspace")

    def run(files: dict[str, str], **job: Any) -> dict[str, Any]:
        job.setdefault("mode", "script")
        job.setdefault("entrypoint", "main.py")
        job.setdefault("max_output_bytes", 65536)
        job["files"] = files
        return json.loads(namespace["run_job"](job))

    return run


class TestScriptMode:
    """Running a program and reporting what it printed."""

    def test_output_and_exit_code(self, driver: Callable[..., dict[str, Any]]) -> None:
        result = driver({"main.py": "print('hello')"})
        assert result["stdout"] == "hello\n"
        assert result["exit_code"] == 0
        assert result["ok"] is True
        assert result["error"] is None

    def test_runs_as_main(self, driver: Callable[..., dict[str, Any]]) -> None:
        """`if __name__ == '__main__':` blocks must fire, as they would locally."""
        result = driver({"main.py": "print(__name__)"})
        assert result["stdout"] == "__main__\n"

    def test_stdin_is_available(self, driver: Callable[..., dict[str, Any]]) -> None:
        result = driver({"main.py": "print(input().upper())"}, stdin="abc\n")
        assert result["stdout"] == "ABC\n"

    def test_sibling_modules_import(self, driver: Callable[..., dict[str, Any]]) -> None:
        result = driver(
            {
                "main.py": "import helper; print(helper.two())",
                "helper.py": "def two(): return 2",
            }
        )
        assert result["stdout"] == "2\n"

    def test_explicit_exit_code_is_preserved(self, driver: Callable[..., dict[str, Any]]) -> None:
        result = driver({"main.py": "import sys; print('bye'); sys.exit(3)"})
        assert result["exit_code"] == 3
        assert result["stdout"] == "bye\n"

    def test_bare_sys_exit_is_success(self, driver: Callable[..., dict[str, Any]]) -> None:
        result = driver({"main.py": "import sys; sys.exit()"})
        assert result["exit_code"] == 0


class TestFailureReporting:
    """What a crash looks like, since the graders read it."""

    def test_a_runtime_error_is_the_learner_failing_not_the_harness(
        self, driver: Callable[..., dict[str, Any]]
    ) -> None:
        """The regression this file was written for: exit 1 with a traceback,
        not exit -2 with an infrastructure error."""
        result = driver({"main.py": "x = 1/0\n"})
        assert result["exit_code"] == 1
        assert result["error"] is None, "a learner bug must not read as engine failure"
        assert "ZeroDivisionError" in result["stderr"]

    def test_the_traceback_starts_at_the_learners_code(
        self, driver: Callable[..., dict[str, Any]]
    ) -> None:
        result = driver({"main.py": "x = 1/0\n"})
        assert "<driver>" not in result["stderr"]
        assert "main.py" in result["stderr"]

    def test_nested_call_frames_are_kept(self, driver: Callable[..., dict[str, Any]]) -> None:
        """Trimming driver noise must not trim the learner's own call chain."""
        result = driver({"main.py": "def boom():\n    return [][5]\nboom()\n"})
        assert result["stderr"].count("main.py") == 2
        assert "IndexError" in result["stderr"]

    def test_a_syntax_error_has_no_empty_traceback_header(
        self, driver: Callable[..., dict[str, Any]]
    ) -> None:
        """SyntaxError is raised at compile time, so there are no frames to show."""
        result = driver({"main.py": "print('unclosed"})
        assert result["exit_code"] == 1
        assert "SyntaxError" in result["stderr"]
        assert "Traceback" not in result["stderr"]

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("int('twelve')", "ValueError"),
            ("undefined_name", "NameError"),
            ("'a' + 1", "TypeError"),
            ("{}['missing']", "KeyError"),
            ("import nonexistent_module_xyz", "ModuleNotFoundError"),
        ],
    )
    def test_the_grader_can_interpret_the_traceback(
        self, driver: Callable[..., dict[str, Any]], source: str, expected: str
    ) -> None:
        """`interpret_traceback` turns these into learner-facing explanations."""
        result = driver({"main.py": source})
        slug, explanation = interpret_traceback(result["stderr"])
        assert slug, f"no misconception derived from a {expected}"
        assert expected in explanation


class TestIsolationBetweenRuns:
    """One run must not contaminate the next; the interpreter is reused."""

    def test_an_edited_module_is_reimported(self, driver: Callable[..., dict[str, Any]]) -> None:
        """Without purging sys.modules a learner's fix would appear to do nothing."""
        driver({"main.py": "import m; print(m.v)", "m.py": "v = 1"})
        result = driver({"main.py": "import m; print(m.v)", "m.py": "v = 2"})
        assert result["stdout"] == "2\n"

    def test_files_written_by_a_previous_run_are_gone(
        self, driver: Callable[..., dict[str, Any]]
    ) -> None:
        driver({"main.py": "open('leak.txt', 'w').write('x')"})
        result = driver({"main.py": "import os; print(os.path.exists('leak.txt'))"})
        assert result["stdout"] == "False\n"


class TestOutputLimits:
    """Truncation, so a runaway print loop cannot exhaust memory."""

    def test_output_is_capped_and_flagged(self, driver: Callable[..., dict[str, Any]]) -> None:
        result = driver({"main.py": "print('x' * 100)"}, max_output_bytes=10)
        assert len(result["stdout"]) == 10
        assert result["stdout_truncated"] is True

    def test_output_within_budget_is_not_flagged(
        self, driver: Callable[..., dict[str, Any]]
    ) -> None:
        result = driver({"main.py": "print('short')"}, max_output_bytes=65536)
        assert result["stdout_truncated"] is False


class TestPytestMode:
    """The pytest grader scores `passed / total` by parsing this output."""

    @pytest.fixture()
    def suite(self, driver: Callable[..., dict[str, Any]]) -> dict[str, Any]:
        return driver(
            {
                "main.py": "def add(a, b):\n    return a + b\n",
                "test_main.py": (
                    "from main import add\n"
                    "def test_ok(): assert add(1, 2) == 3\n"
                    "def test_bad(): assert add(1, 1) == 3\n"
                ),
            },
            mode="pytest",
            pytest_args=PYTEST_ARGS,
        )

    def test_per_test_outcomes_are_attributable(self, suite: dict[str, Any]) -> None:
        combined = f"{suite['stdout']}\n{suite['stderr']}"
        cases = {
            match.group("node").split("::")[-1]: match.group("outcome")
            for match in (_PYTEST_CASE.match(line) for line in combined.splitlines())
            if match
        }
        assert cases == {"test_ok": "PASSED", "test_bad": "FAILED"}

    def test_the_tally_supports_a_partial_score(self, suite: dict[str, Any]) -> None:
        combined = f"{suite['stdout']}\n{suite['stderr']}"
        tallies = {kind: int(count) for count, kind in _PYTEST_TALLY.findall(combined)}
        assert tallies.get("passed") == 1
        assert tallies.get("failed") == 1

    def test_a_failing_suite_exits_nonzero(self, suite: dict[str, Any]) -> None:
        assert suite["exit_code"] != 0

    def test_an_all_passing_suite_exits_zero(self, driver: Callable[..., dict[str, Any]]) -> None:
        result = driver(
            {
                "main.py": "def add(a, b):\n    return a + b\n",
                "test_main.py": "from main import add\ndef test_ok(): assert add(1, 2) == 3\n",
            },
            mode="pytest",
            pytest_args=PYTEST_ARGS,
        )
        assert result["exit_code"] == 0
        assert result["ok"] is True
