"""Tests for the graders and the traceback interpreter."""

from __future__ import annotations

import pytest

from app.execution.base import ExecutionResult
from app.models import Exercise
from app.models.enums import GraderKind, SubmissionStatus
from app.services.grading import (
    grade,
    grade_multiple_choice,
    grade_pytest,
    grade_static_assert,
    grade_stdout_match,
    interpret_traceback,
    normalise_output,
)


def make_exercise(**kwargs) -> Exercise:
    """Build an unsaved exercise for grader tests."""
    defaults = {
        "slug": "test-exercise",
        "title": "Test",
        "prompt": "",
        "grader": GraderKind.STDOUT_MATCH.value,
        "grader_config": {},
        "concept_slugs": ["variables"],
        "misconception_rules": [],
        "starter_files": {},
        "hidden_files": {},
        "solution_files": {},
    }
    return Exercise(**{**defaults, **kwargs})


def ok(stdout: str = "", stderr: str = "", exit_code: int = 0) -> ExecutionResult:
    return ExecutionResult(
        ok=exit_code == 0,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=False,
        duration_ms=5,
    )


class TestNormalisation:
    def test_strips_trailing_whitespace_per_line(self):
        assert normalise_output("a   \nb\t\n") == "a\nb"

    def test_drops_trailing_blank_lines(self):
        assert normalise_output("a\n\n\n") == "a"

    def test_preserves_internal_blank_lines(self):
        assert normalise_output("a\n\nb") == "a\n\nb"

    def test_normalises_crlf(self):
        assert normalise_output("a\r\nb") == "a\nb"


class TestStdoutGrader:
    def test_exact_match_passes(self):
        exercise = make_exercise(grader_config={"expected_stdout": "Hello"})
        result = grade_stdout_match(exercise, ok("Hello\n"))
        assert result.passed
        assert result.score == 1.0

    def test_mismatch_fails_with_a_diff(self):
        exercise = make_exercise(grader_config={"expected_stdout": "Hello"})
        result = grade_stdout_match(exercise, ok("Goodbye\n"))
        assert not result.passed
        assert result.checks[0].diff
        assert "output-mismatch" in result.misconceptions

    def test_case_insensitive_mode(self):
        exercise = make_exercise(grader_config={"expected_stdout": "Hello", "ignore_case": True})
        assert grade_stdout_match(exercise, ok("HELLO")).passed

    def test_crash_is_reported_as_an_error(self):
        exercise = make_exercise(grader_config={"expected_stdout": "Hello"})
        result = grade_stdout_match(
            exercise, ok(stderr="NameError: name 'x' is not defined", exit_code=1)
        )
        assert result.status is SubmissionStatus.ERROR
        assert "undefined-name" in result.misconceptions

    def test_timeout_is_reported_distinctly(self):
        exercise = make_exercise(grader_config={"expected_stdout": "Hello"})
        timed_out = ExecutionResult(
            ok=False, exit_code=-1, stdout="", stderr="", timed_out=True, duration_ms=2000
        )
        result = grade_stdout_match(exercise, timed_out)
        assert result.status is SubmissionStatus.TIMED_OUT
        assert "infinite-loop" in result.misconceptions


class TestPytestGrader:
    PASSING = "test_x.py::test_one PASSED\ntest_x.py::test_two PASSED\n2 passed in 0.02s\n"
    MIXED = "test_x.py::test_one PASSED\ntest_x.py::test_two FAILED\n1 passed, 1 failed in 0.03s\n"

    def test_all_passing(self):
        result = grade_pytest(make_exercise(), ok(self.PASSING))
        assert result.passed
        assert result.score == 1.0
        assert len(result.checks) == 2

    def test_partial_pass_is_partial(self):
        result = grade_pytest(make_exercise(), ok(self.MIXED, exit_code=1))
        assert result.status is SubmissionStatus.PARTIAL
        assert result.score == pytest.approx(0.5)

    def test_collection_error_is_an_error(self):
        result = grade_pytest(
            make_exercise(),
            ok(stderr="ImportError: cannot import name 'add'", exit_code=2),
        )
        assert result.status is SubmissionStatus.ERROR
        assert result.score == 0.0

    def test_authored_misconception_rules_apply(self):
        exercise = make_exercise(
            misconception_rules=[{"pattern": "test_two", "misconception": "custom-misconception"}]
        )
        result = grade_pytest(exercise, ok(self.MIXED, exit_code=1))
        assert "custom-misconception" in result.misconceptions

    def test_invalid_regex_in_a_rule_does_not_crash(self):
        exercise = make_exercise(
            misconception_rules=[{"pattern": "[unclosed", "misconception": "x"}]
        )
        assert grade_pytest(exercise, ok(self.MIXED, exit_code=1)) is not None


class TestStaticGrader:
    def test_detects_a_defined_function(self):
        exercise = make_exercise(
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"assertions": [{"kind": "defines_function", "name": "total"}]},
        )
        result = grade_static_assert(exercise, {"main.py": "def total(x):\n    return x"})
        assert result.passed

    def test_requires_a_construct(self):
        exercise = make_exercise(
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"assertions": [{"kind": "uses_construct", "node": "ListComp"}]},
        )
        assert grade_static_assert(exercise, {"main.py": "x = [i for i in range(3)]"}).passed
        assert not grade_static_assert(
            exercise, {"main.py": "x = []\nfor i in range(3):\n    x.append(i)"}
        ).passed

    def test_forbids_a_construct(self):
        exercise = make_exercise(
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"assertions": [{"kind": "forbids_construct", "node": "For"}]},
        )
        assert grade_static_assert(exercise, {"main.py": "x = [1]"}).passed
        assert not grade_static_assert(exercise, {"main.py": "for i in range(3):\n    pass"}).passed

    def test_construct_inside_a_string_does_not_count(self):
        """AST-based checking, not text search."""
        exercise = make_exercise(
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"assertions": [{"kind": "uses_construct", "node": "For"}]},
        )
        result = grade_static_assert(exercise, {"main.py": "note = 'use a for loop here'\n"})
        assert not result.passed

    def test_type_hint_assertion(self):
        exercise = make_exercise(
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"assertions": [{"kind": "has_type_hints", "name": "f"}]},
        )
        assert grade_static_assert(
            exercise, {"main.py": "def f(x: int) -> int:\n    return x"}
        ).passed
        assert not grade_static_assert(exercise, {"main.py": "def f(x):\n    return x"}).passed

    def test_syntax_error_is_reported_with_a_line_number(self):
        exercise = make_exercise(
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"assertions": [{"kind": "defines_function", "name": "f"}]},
        )
        result = grade_static_assert(exercise, {"main.py": "def f(:\n"})
        assert result.status is SubmissionStatus.ERROR
        assert "syntax-error" in result.misconceptions

    def test_empty_submission(self):
        exercise = make_exercise(
            grader=GraderKind.STATIC_ASSERT.value,
            grader_config={"assertions": [{"kind": "defines_function", "name": "f"}]},
        )
        result = grade_static_assert(exercise, {"main.py": "   "})
        assert not result.passed
        assert "empty-submission" in result.misconceptions


class TestMultipleChoiceGrader:
    def test_correct_answer(self):
        exercise = make_exercise(
            grader=GraderKind.MULTIPLE_CHOICE.value,
            grader_config={"options": ["a", "b"], "correct_index": 1, "explanation": "b it is"},
        )
        result = grade_multiple_choice(exercise, 1)
        assert result.passed
        assert result.feedback == "b it is"

    def test_wrong_answer_maps_to_a_misconception(self):
        exercise = make_exercise(
            grader=GraderKind.MULTIPLE_CHOICE.value,
            grader_config={
                "options": ["a", "b"],
                "correct_index": 1,
                "misconception_per_option": {"0": "aliasing"},
            },
        )
        result = grade_multiple_choice(exercise, 0)
        assert not result.passed
        assert result.misconceptions == ["aliasing"]

    def test_no_answer_selected(self):
        exercise = make_exercise(
            grader=GraderKind.MULTIPLE_CHOICE.value,
            grader_config={"options": ["a", "b"], "correct_index": 1},
        )
        assert not grade_multiple_choice(exercise, -1).passed


class TestTracebackInterpretation:
    @pytest.mark.parametrize(
        "stderr,expected",
        [
            ("NameError: name 'x' is not defined", "undefined-name"),
            ("TypeError: can only concatenate str", "type-mismatch"),
            ("IndexError: list index out of range", "off-by-one"),
            ("KeyError: 'port'", "missing-key"),
            ("ZeroDivisionError: division by zero", "unguarded-division"),
            ("RecursionError: maximum recursion depth exceeded", "runaway-recursion"),
            ("ModuleNotFoundError: No module named 'requests'", "missing-import"),
        ],
    )
    def test_recognises_common_errors(self, stderr, expected):
        slug, explanation = interpret_traceback(stderr)
        assert slug == expected
        assert explanation

    def test_empty_stderr_yields_nothing(self):
        assert interpret_traceback("") == (None, "")

    def test_unknown_exception_falls_back(self):
        slug, explanation = interpret_traceback("WeirdCustomError: something")
        assert slug == "runtime-error"
        assert explanation


class TestDispatch:
    def test_engine_failure_is_reported_as_an_error(self):
        exercise = make_exercise()
        failure = ExecutionResult.infrastructure_failure("engine down")
        result = grade(exercise, files={}, result=failure)
        assert result.status is SubmissionStatus.ERROR
        assert "unavailable" in result.feedback

    def test_missing_execution_result_is_handled(self):
        result = grade(make_exercise(), files={}, result=None)
        assert result.status is SubmissionStatus.ERROR
