"""Tests for the code review engine."""

from __future__ import annotations

from app.services.code_review import Dimension, Severity, review_files


def findings_for(source: str, dimension: Dimension | None = None):
    result = review_files({"main.py": source})
    if dimension is None:
        return result.findings
    return [f for f in result.findings if f.dimension is dimension]


class TestSecurityFindings:
    def test_flags_eval(self):
        findings = findings_for("x = eval(user_input)", Dimension.SECURITY)
        assert any(f.severity is Severity.CRITICAL for f in findings)

    def test_flags_os_system(self):
        assert findings_for("import os\nos.system('ls ' + name)", Dimension.SECURITY)

    def test_flags_shell_true(self):
        source = "import subprocess\nsubprocess.run(cmd, shell=True)"
        assert findings_for(source, Dimension.SECURITY)

    def test_allows_subprocess_with_an_argument_list(self):
        source = "import subprocess\nsubprocess.run(['ls', '-l'])"
        assert not findings_for(source, Dimension.SECURITY)

    def test_flags_hardcoded_secret(self):
        findings = findings_for('API_KEY = "sk-live-abcdef123456"', Dimension.SECURITY)
        assert findings
        assert "secret" in findings[0].message.lower()

    def test_flags_sql_built_with_an_fstring(self):
        source = 'q = f"SELECT * FROM users WHERE id = {user_id}"'
        assert findings_for(source, Dimension.SECURITY)

    def test_flags_sql_built_by_concatenation(self):
        source = 'q = "SELECT * FROM users WHERE id = " + str(user_id)'
        assert findings_for(source, Dimension.SECURITY)

    def test_parameterised_sql_is_clean(self):
        source = 'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))'
        assert not findings_for(source, Dimension.SECURITY)


class TestCorrectnessFindings:
    def test_flags_mutable_default_argument(self):
        findings = findings_for("def f(x, acc=[]):\n    return acc", Dimension.CORRECTNESS)
        assert any(f.severity is Severity.CRITICAL for f in findings)

    def test_sentinel_default_is_clean(self):
        source = "def f(x, acc=None):\n    if acc is None:\n        acc = []\n    return acc"
        assert not findings_for(source, Dimension.CORRECTNESS)

    def test_flags_identity_comparison_with_a_literal(self):
        assert findings_for("if x is 5:\n    pass", Dimension.CORRECTNESS)

    def test_identity_comparison_with_none_is_fine(self):
        assert not findings_for("if x is None:\n    pass", Dimension.CORRECTNESS)

    def test_flags_open_outside_a_with_block(self):
        assert findings_for("f = open('data.txt')", Dimension.CORRECTNESS)

    def test_open_inside_with_is_clean(self):
        source = "with open('data.txt') as f:\n    data = f.read()"
        assert not findings_for(source, Dimension.CORRECTNESS)


class TestErrorHandlingFindings:
    def test_flags_bare_except(self):
        source = "try:\n    risky()\nexcept:\n    handle()"
        findings = findings_for(source, Dimension.ERROR_HANDLING)
        assert any(f.severity is Severity.CRITICAL for f in findings)

    def test_flags_broad_except(self):
        source = "try:\n    risky()\nexcept Exception:\n    handle()"
        assert findings_for(source, Dimension.ERROR_HANDLING)

    def test_flags_silent_pass(self):
        source = "try:\n    risky()\nexcept ValueError:\n    pass"
        findings = findings_for(source, Dimension.ERROR_HANDLING)
        assert any("swallow" in f.message.lower() for f in findings)

    def test_specific_handler_with_a_body_is_clean(self):
        source = (
            "import logging\ntry:\n    risky()\nexcept ValueError:\n    logging.exception('failed')"
        )
        assert not findings_for(source, Dimension.ERROR_HANDLING)


class TestComplexityAndStyle:
    def test_flags_high_cyclomatic_complexity(self):
        branches = "\n".join(f"    if x == {n}:\n        return {n}" for n in range(15))
        source = f"def f(x):\n{branches}\n    return None"
        assert findings_for(source, Dimension.COMPLEXITY)

    def test_flags_too_many_parameters(self):
        source = "def f(a, b, c, d, e, f_, g, h):\n    return a"
        assert findings_for(source, Dimension.MAINTAINABILITY)

    def test_flags_range_len_iteration(self):
        source = "for i in range(len(items)):\n    print(items[i])"
        assert findings_for(source, Dimension.READABILITY)

    def test_flags_long_lines(self):
        source = "x = " + '"' + "a" * 200 + '"'
        assert findings_for(source, Dimension.PEP8)

    def test_flags_non_snake_case_function(self):
        assert findings_for("def MyFunction():\n    pass", Dimension.NAMING)

    def test_flags_non_capwords_class(self):
        assert findings_for('class my_class:\n    """Doc."""', Dimension.NAMING)


class TestTestability:
    def test_flags_work_at_import_time(self):
        source = "def run():\n    pass\n\nrun()"
        assert findings_for(source, Dimension.TESTABILITY)

    def test_main_guard_is_clean(self):
        source = 'def run():\n    pass\n\n\nif __name__ == "__main__":\n    run()'
        assert not findings_for(source, Dimension.TESTABILITY)


class TestAggregate:
    def test_clean_code_scores_well_and_lists_strengths(self):
        source = '''\
"""A tidy module."""


def add(left: int, right: int) -> int:
    """Return the sum of two integers."""
    return left + right


if __name__ == "__main__":
    print(add(1, 2))
'''
        result = review_files({"main.py": source})
        assert result.overall_score > 0.9
        assert result.strengths
        assert "approve" in result.summary.lower()

    def test_bad_code_requests_changes(self):
        source = "def f(x, acc=[]):\n    try:\n        return eval(x)\n    except:\n        pass"
        result = review_files({"main.py": source})
        assert result.overall_score < 0.7
        assert "request changes" in result.summary.lower()

    def test_syntax_error_is_a_critical_finding(self):
        result = review_files({"main.py": "def broken(:"})
        assert any(f.severity is Severity.CRITICAL for f in result.findings)

    def test_reviews_multiple_files(self):
        result = review_files({"a.py": "x = eval('1')", "b.py": "y = eval('2')"})
        files = {finding.file for finding in result.findings}
        assert files == {"a.py", "b.py"}

    def test_no_python_files_is_handled(self):
        result = review_files({"README.md": "# hello"})
        assert result.overall_score == 0.0
        assert "No Python source" in result.summary

    def test_every_dimension_is_scored(self):
        result = review_files({"main.py": "x = 1"})
        assert set(result.dimension_scores) == {d.value for d in Dimension}
