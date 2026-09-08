"""The vendored browser grader must agree with the real one.

``tools/export_static.py`` ships ``app/services/grading.py`` into the browser by
stripping its four application imports and substituting shims. That is only safe
while the shims are faithful: if someone adds a dependency to grading.py, or
changes what ``Exercise`` exposes, the generated module could still import and
yet grade differently — which would mean learners on the published site being
told they passed when they did not.

So these tests grade the same submissions twice, once through each
implementation, and require identical verdicts.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.execution.base import ExecutionResult
from app.models import Exercise
from app.models.enums import GraderKind, SubmissionStatus
from app.services.grading import grade as real_grade

REPO = Path(__file__).resolve().parents[2]
EXPORTER = REPO / "tools" / "export_static.py"


@pytest.fixture(scope="module")
def vendored(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """Generate the browser grader and import it."""
    out = tmp_path_factory.mktemp("static")
    subprocess.run(  # noqa: S603
        [sys.executable, str(EXPORTER), "--out", str(out)],
        check=True,
        capture_output=True,
        cwd=REPO,
    )
    path = out / "grader.py"
    assert path.exists(), "the exporter did not emit grader.py"

    spec = importlib.util.spec_from_file_location("pyforge_vendored_grader", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves string annotations through sys.modules, and Pyodide
    # execs this into __main__ which is always registered. Mirror that here.
    sys.modules["pyforge_vendored_grader"] = module
    spec.loader.exec_module(module)
    return module


def _exercise(**fields: Any) -> Exercise:
    """An unsaved exercise row carrying just what grading reads."""
    row = Exercise(
        slug=fields.get("slug", "demo"),
        title="Demo",
        prompt="Demo",
        grader=fields["grader"],
        grader_config=fields.get("grader_config", {}),
        misconception_rules=fields.get("misconception_rules", []),
    )
    return row


def _both(
    vendored: Any,
    *,
    grader: str,
    grader_config: dict[str, Any],
    files: dict[str, str],
    execution: dict[str, Any] | None = None,
    selected_index: int | None = None,
    misconception_rules: list[dict[str, str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Grade one submission through both implementations."""
    row = _exercise(
        grader=grader,
        grader_config=grader_config,
        misconception_rules=misconception_rules or [],
    )
    result = real_grade(
        row,
        files=files,
        result=ExecutionResult(**execution) if execution is not None else None,
        selected_index=selected_index,
    )
    mine = {
        "status": result.status.value,
        "score": result.score,
        "checks": [check.to_dict() for check in result.checks],
        "feedback": result.feedback,
        "misconceptions": result.misconceptions,
    }

    theirs = json.loads(
        vendored.grade_submission(
            {
                "exercise": {
                    "slug": row.slug,
                    "grader": grader,
                    "grader_config": grader_config,
                    "misconception_rules": misconception_rules or [],
                },
                "files": files,
                "execution": (
                    None
                    if execution is None
                    else {
                        "exit_code": execution.get("exit_code", 1),
                        "stdout": execution.get("stdout", ""),
                        "stderr": execution.get("stderr", ""),
                        "timed_out": execution.get("timed_out", False),
                        "duration_ms": execution.get("duration_ms", 0),
                        "error": execution.get("error"),
                    }
                ),
                "selected_index": selected_index,
            }
        )
    )
    return mine, theirs


def _execution(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ok": False,
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "duration_ms": 5,
    }
    base.update(overrides)
    base["ok"] = base["exit_code"] == 0
    return base


class TestTheGeneratedModuleIsUsable:
    """Basic sanity on the artefact itself."""

    def test_it_exposes_the_entry_point(self, vendored: Any) -> None:
        assert callable(vendored.grade_submission)

    def test_it_carries_the_real_graders(self, vendored: Any) -> None:
        """Proof it is the actual module, not a reimplementation."""
        for name in ("grade_stdout_match", "grade_pytest", "grade_static_assert", "grade"):
            assert hasattr(vendored, name), f"vendored grader is missing {name}"

    def test_no_application_imports_survive(self, vendored: Any) -> None:
        source = Path(vendored.__file__).read_text(encoding="utf-8")
        assert "from app." not in source
        assert "import app" not in source


class TestStdoutMatchAgrees:
    """The simplest grader, and the one most exercises start with."""

    CONFIG = {"expected_stdout": "Hello, world!\n"}

    def test_a_correct_answer(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STDOUT_MATCH.value,
            grader_config=self.CONFIG,
            files={"main.py": "print('Hello, world!')"},
            execution=_execution(stdout="Hello, world!\n"),
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.PASSED.value

    def test_a_wrong_answer_including_the_diff(self, vendored: Any) -> None:
        """The diff is learner-facing text, so it has to match character for character."""
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STDOUT_MATCH.value,
            grader_config=self.CONFIG,
            files={"main.py": "print('nope')"},
            execution=_execution(stdout="nope\n"),
        )
        assert mine == theirs
        assert mine["checks"][0]["diff"]

    def test_trailing_whitespace_is_forgiven_identically(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STDOUT_MATCH.value,
            grader_config=self.CONFIG,
            files={"main.py": "x"},
            execution=_execution(stdout="Hello, world!   \n\n\n"),
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.PASSED.value

    def test_a_crash(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STDOUT_MATCH.value,
            grader_config=self.CONFIG,
            files={"main.py": "1/0"},
            execution=_execution(
                exit_code=1, stderr="Traceback...\nZeroDivisionError: division by zero"
            ),
        )
        assert mine == theirs
        assert mine["misconceptions"] == ["unguarded-division"]

    def test_a_timeout(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STDOUT_MATCH.value,
            grader_config=self.CONFIG,
            files={"main.py": "while True: pass"},
            execution=_execution(exit_code=-1, timed_out=True),
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.TIMED_OUT.value

    def test_an_engine_failure(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STDOUT_MATCH.value,
            grader_config=self.CONFIG,
            files={"main.py": "x"},
            execution=_execution(exit_code=-2, error="the engine did not start"),
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.ERROR.value

    @pytest.mark.parametrize(
        "stderr",
        [
            "NameError: name 'x' is not defined",
            "TypeError: can only concatenate str",
            "IndexError: list index out of range",
            "KeyError: 'missing'",
            "ModuleNotFoundError: No module named 'requests'",
            "RecursionError: maximum recursion depth exceeded",
            "IndentationError: unexpected indent",
            "some text that is not a traceback at all",
        ],
    )
    def test_every_misconception_is_derived_identically(
        self, vendored: Any, stderr: str
    ) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STDOUT_MATCH.value,
            grader_config=self.CONFIG,
            files={"main.py": "x"},
            execution=_execution(exit_code=1, stderr=stderr),
        )
        assert mine == theirs


class TestPytestAgrees:
    """Scored `passed / total` off the driver's verbose output."""

    def test_all_passing(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.PYTEST.value,
            grader_config={},
            files={"main.py": "def add(a, b): return a + b"},
            execution=_execution(
                stdout="test_main.py::test_add PASSED\n1 passed in 0.01s",
            ),
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.PASSED.value

    def test_partially_passing(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.PYTEST.value,
            grader_config={},
            files={"main.py": "x"},
            execution=_execution(
                exit_code=1,
                stdout=(
                    "test_main.py::test_a PASSED\n"
                    "test_main.py::test_b FAILED\n"
                    "1 passed, 1 failed in 0.02s"
                ),
            ),
        )
        assert mine == theirs
        assert mine["score"] == 0.5
        assert len(mine["checks"]) == 2

    def test_a_collection_error(self, vendored: Any) -> None:
        """A suite that never ran must not score as zero-of-zero."""
        mine, theirs = _both(
            vendored,
            grader=GraderKind.PYTEST.value,
            grader_config={},
            files={"main.py": "def broken("},
            execution=_execution(exit_code=2, stderr="SyntaxError: invalid syntax"),
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.ERROR.value

    def test_authored_misconception_rules_apply(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.PYTEST.value,
            grader_config={},
            files={"main.py": "x"},
            misconception_rules=[{"pattern": "off.by.one", "misconception": "off-by-one"}],
            execution=_execution(
                exit_code=1,
                stdout="test_main.py::test_a FAILED\n1 failed in 0.01s\nassert off by one",
            ),
        )
        assert mine == theirs
        assert "off-by-one" in mine["misconceptions"]

    def test_an_invalid_authored_pattern_does_not_crash_either(self, vendored: Any) -> None:
        """A bad regex is an author mistake; both must survive it the same way."""
        mine, theirs = _both(
            vendored,
            grader=GraderKind.PYTEST.value,
            grader_config={},
            files={"main.py": "x"},
            misconception_rules=[{"pattern": "([unclosed", "misconception": "whatever"}],
            execution=_execution(exit_code=1, stdout="test_a FAILED\n1 failed in 0.01s"),
        )
        assert mine == theirs


class TestStaticAssertAgrees:
    """AST assertions — the reason grading runs in Python rather than TypeScript."""

    @pytest.mark.parametrize(
        ("assertions", "source"),
        [
            ([{"kind": "defines_function", "name": "total"}], "def total(x): return x"),
            ([{"kind": "defines_function", "name": "total"}], "def other(x): return x"),
            ([{"kind": "defines_class", "name": "Cart"}], "class Cart: pass"),
            ([{"kind": "uses_construct", "node": "ListComp"}], "xs = [i for i in range(3)]"),
            ([{"kind": "uses_construct", "node": "ListComp"}], "xs = []"),
            ([{"kind": "forbids_construct", "node": "For"}], "for i in range(3): pass"),
            ([{"kind": "forbids_construct", "node": "For"}], "xs = [i for i in range(3)]"),
            ([{"kind": "calls_function", "name": "print"}], "print('hi')"),
            ([{"kind": "imports_module", "name": "pathlib"}], "import pathlib"),
            ([{"kind": "imports_module", "name": "pathlib"}], "from pathlib import Path"),
            ([{"kind": "max_lines", "value": 2}], "a = 1\nb = 2\nc = 3"),
            ([{"kind": "has_docstring", "name": "f"}], 'def f():\n    """Doc."""\n    pass'),
            ([{"kind": "has_docstring"}], '"""Module doc."""\nx = 1'),
            ([{"kind": "has_type_hints", "name": "f"}], "def f(a: int) -> int: return a"),
            ([{"kind": "has_type_hints", "name": "f"}], "def f(a): return a"),
            # A construct that only appears inside a string must not count.
            ([{"kind": "uses_construct", "node": "For"}], "s = 'for i in range(3)'"),
            # An author typo naming a non-existent AST node.
            ([{"kind": "uses_construct", "node": "NotARealNode"}], "x = 1"),
            # An unknown assertion kind.
            ([{"kind": "no_such_assertion"}], "x = 1"),
        ],
    )
    def test_each_assertion_kind(
        self, vendored: Any, assertions: list[dict[str, Any]], source: str
    ) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"target_file": "main.py", "assertions": assertions},
            files={"main.py": source},
        )
        assert mine == theirs

    def test_a_syntax_error(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={
                "target_file": "main.py",
                "assertions": [{"kind": "defines_function", "name": "f"}],
            },
            files={"main.py": "def f(:"},
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.ERROR.value

    def test_an_empty_file(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"target_file": "main.py", "assertions": []},
            files={"main.py": "   \n"},
        )
        assert mine == theirs
        assert mine["misconceptions"] == ["empty-submission"]


class TestMultipleChoiceAgrees:
    """Concept checks, including the per-option misconception mapping."""

    CONFIG = {
        "options": ["first", "second", "third"],
        "correct_index": 1,
        "explanation": "Because reasons.",
        "misconception_per_option": {"0": "picked-first", "2": "picked-third"},
    }

    @pytest.mark.parametrize("selected", [0, 1, 2, -1, 99])
    def test_each_option_including_out_of_range(self, vendored: Any, selected: int) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.MULTIPLE_CHOICE.value,
            grader_config=self.CONFIG,
            files={},
            selected_index=selected,
        )
        assert mine == theirs

    def test_no_answer_at_all(self, vendored: Any) -> None:
        mine, theirs = _both(
            vendored,
            grader=GraderKind.MULTIPLE_CHOICE.value,
            grader_config=self.CONFIG,
            files={},
            selected_index=None,
        )
        assert mine == theirs
        assert mine["status"] == SubmissionStatus.FAILED.value


class TestRealExportedExercises:
    """Every exercise the published site will actually serve."""

    def test_each_seeded_exercise_grades_the_same_both_ways(
        self, vendored: Any, seeded_session: Any
    ) -> None:
        """Catches an exercise whose authored config the shim mishandles."""
        from sqlalchemy import select

        rows = seeded_session.scalars(select(Exercise)).all()
        assert rows, "the seed curriculum should contain exercises"

        for row in rows:
            grader = GraderKind(row.grader)
            execution: dict[str, Any] | None = None
            files = dict(row.solution_files or {"main.py": "x = 1"})
            selected: int | None = None

            if grader is GraderKind.STDOUT_MATCH:
                execution = _execution(stdout=row.grader_config.get("expected_stdout", ""))
            elif grader is GraderKind.PYTEST:
                execution = _execution(stdout="t.py::test_a PASSED\n1 passed in 0.01s")
            elif grader is GraderKind.MULTIPLE_CHOICE:
                selected = int(row.grader_config.get("correct_index", 0))

            mine, theirs = _both(
                vendored,
                grader=row.grader,
                grader_config=dict(row.grader_config),
                files=files,
                execution=execution,
                selected_index=selected,
                misconception_rules=list(row.misconception_rules),
            )
            assert mine == theirs, f"graders disagree on {row.slug}"
