"""The code review engine.

Produces a senior-engineer-style review across the eleven dimensions in spec
§37. The static analysis here is deliberately deterministic — it runs without
network access, gives the same answer every time, and is what the learner is
graded against. When an AI backend is configured, :mod:`app.services.ai_tutor`
can add prose commentary *on top of* these findings; it never replaces them.

Every finding carries a severity, a line number where possible, and a
suggestion. Findings are advisory: the review score never changes an exercise
grade, but it does feed the *maintainability* signals on the dashboard.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

MAX_LINE_LENGTH = 100
MAX_FUNCTION_LINES = 50
MAX_PARAMETERS = 6
MAX_NESTING_DEPTH = 4
MAX_CYCLOMATIC_COMPLEXITY = 10


class Severity(StrEnum):
    """How much a finding matters."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class Dimension(StrEnum):
    """Review dimensions from the specification."""

    CORRECTNESS = "correctness"
    READABILITY = "readability"
    MAINTAINABILITY = "maintainability"
    PEP8 = "pep8"
    NAMING = "naming"
    COMPLEXITY = "complexity"
    ERROR_HANDLING = "error_handling"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTABILITY = "testability"
    ARCHITECTURE = "architecture"


_SEVERITY_COST = {
    Severity.CRITICAL: 0.34,
    Severity.MAJOR: 0.18,
    Severity.MINOR: 0.07,
    Severity.INFO: 0.0,
}


@dataclass(slots=True)
class Finding:
    """One review observation."""

    dimension: Dimension
    severity: Severity
    message: str
    suggestion: str
    file: str = "main.py"
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise for storage and the API."""
        return {
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "file": self.file,
            "line": self.line,
        }


@dataclass(slots=True)
class ReviewResult:
    """A complete review."""

    findings: list[Finding] = field(default_factory=list)
    dimension_scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 1.0
    summary: str = ""
    strengths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise for storage and the API."""
        return {
            "findings": [finding.to_dict() for finding in self.findings],
            "dimension_scores": self.dimension_scores,
            "overall_score": round(self.overall_score, 4),
            "summary": self.summary,
            "strengths": self.strengths,
        }


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


class _Analyzer(ast.NodeVisitor):
    """Walks one module and collects findings."""

    def __init__(self, filename: str, source: str) -> None:
        self.filename = filename
        self.source = source
        self.lines = source.splitlines()
        self.findings: list[Finding] = []
        self.function_count = 0
        self.documented_functions = 0
        self.annotated_functions = 0
        self.has_module_docstring = False
        self._depth = 0
        self._with_context_lines: set[int] = set()

    # -- helpers ------------------------------------------------------------

    def _add(
        self,
        dimension: Dimension,
        severity: Severity,
        message: str,
        suggestion: str,
        line: int | None = None,
    ) -> None:
        self.findings.append(Finding(dimension, severity, message, suggestion, self.filename, line))

    # -- visitors -----------------------------------------------------------

    def visit_Module(self, node: ast.Module) -> None:  # noqa: N802
        """Check module-level concerns and index ``with`` context lines."""
        self.has_module_docstring = ast.get_docstring(node) is not None
        self._with_context_lines = {
            item.context_expr.lineno
            for candidate in ast.walk(node)
            if isinstance(candidate, ast.With | ast.AsyncWith)
            for item in candidate.items
            if hasattr(item.context_expr, "lineno")
        }
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Check one function definition."""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """Check one async function definition."""
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.function_count += 1

        if ast.get_docstring(node):
            self.documented_functions += 1
        elif not node.name.startswith("_"):
            self._add(
                Dimension.READABILITY,
                Severity.MINOR,
                f"`{node.name}()` has no docstring.",
                "State what it does, what it takes and what it returns. One sentence is enough.",
                node.lineno,
            )

        params = [
            a for a in [*node.args.args, *node.args.kwonlyargs] if a.arg not in {"self", "cls"}
        ]
        if params and all(a.annotation is not None for a in params) and node.returns is not None:
            self.annotated_functions += 1

        if len(params) > MAX_PARAMETERS:
            self._add(
                Dimension.MAINTAINABILITY,
                Severity.MAJOR,
                f"`{node.name}()` takes {len(params)} parameters.",
                "Group related parameters into a dataclass, or split the function — a long "
                "parameter list usually means it is doing more than one job.",
                node.lineno,
            )

        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        length = end - node.lineno
        if length > MAX_FUNCTION_LINES:
            self._add(
                Dimension.COMPLEXITY,
                Severity.MAJOR,
                f"`{node.name}()` is {length} lines long.",
                f"Extract cohesive blocks into helpers; aim for under {MAX_FUNCTION_LINES} lines "
                "so the whole function fits on one screen.",
                node.lineno,
            )

        complexity = _cyclomatic_complexity(node)
        if complexity > MAX_CYCLOMATIC_COMPLEXITY:
            self._add(
                Dimension.COMPLEXITY,
                Severity.MAJOR,
                f"`{node.name}()` has a cyclomatic complexity of {complexity}.",
                "Each branch is another path to test. Use early returns, or pull decision "
                "logic into a lookup table.",
                node.lineno,
            )

        depth = _max_nesting(node)
        if depth > MAX_NESTING_DEPTH:
            self._add(
                Dimension.READABILITY,
                Severity.MINOR,
                f"`{node.name}()` nests {depth} levels deep.",
                "Invert conditions and return early to flatten the body.",
                node.lineno,
            )

        for default in node.args.defaults + [d for d in node.args.kw_defaults if d]:
            if isinstance(default, ast.List | ast.Dict | ast.Set | ast.Call):
                self._add(
                    Dimension.CORRECTNESS,
                    Severity.CRITICAL,
                    f"`{node.name}()` has a mutable default argument.",
                    "Defaults are evaluated once, at definition time, and then shared between "
                    "calls. Use `None` and create the value inside the function.",
                    node.lineno,
                )

        if not re.fullmatch(r"[a-z_][a-z0-9_]*", node.name) and not node.name.startswith("__"):
            self._add(
                Dimension.NAMING,
                Severity.MINOR,
                f"`{node.name}` is not snake_case.",
                "PEP 8 asks for lower_case_with_underscores for functions and methods.",
                node.lineno,
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """Check class naming and documentation."""
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", node.name):
            self._add(
                Dimension.NAMING,
                Severity.MINOR,
                f"Class `{node.name}` is not CapWords.",
                "PEP 8 asks for CapitalisedWords for class names.",
                node.lineno,
            )
        if ast.get_docstring(node) is None:
            self._add(
                Dimension.READABILITY,
                Severity.MINOR,
                f"Class `{node.name}` has no docstring.",
                "Say what the class represents and what invariants it maintains.",
                node.lineno,
            )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
        """Flag bare and over-broad exception handling."""
        if node.type is None:
            self._add(
                Dimension.ERROR_HANDLING,
                Severity.CRITICAL,
                "Bare `except:` catches everything, including KeyboardInterrupt.",
                "Catch the specific exception you can actually handle, e.g. `except ValueError:`.",
                node.lineno,
            )
        elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            self._add(
                Dimension.ERROR_HANDLING,
                Severity.MAJOR,
                f"`except {node.type.id}` is very broad.",
                "Narrow it to the failures you expect, so genuine bugs still surface.",
                node.lineno,
            )
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self._add(
                Dimension.ERROR_HANDLING,
                Severity.CRITICAL,
                "This handler swallows the exception silently.",
                "At minimum log it. A silent `pass` turns a bug into a mystery.",
                node.lineno,
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Flag dangerous calls."""
        name = _call_name(node)
        if name in {"eval", "exec"}:
            self._add(
                Dimension.SECURITY,
                Severity.CRITICAL,
                f"`{name}()` executes arbitrary code.",
                "If the input is ever influenced by a user this is remote code execution. "
                "Use `ast.literal_eval`, a dict dispatch, or `json.loads`.",
                node.lineno,
            )
        elif name == "pickle.loads":
            self._add(
                Dimension.SECURITY,
                Severity.CRITICAL,
                "`pickle.loads` on untrusted data executes arbitrary code.",
                "Use JSON for data you did not produce yourself.",
                node.lineno,
            )
        elif name in {"os.system", "os.popen"}:
            self._add(
                Dimension.SECURITY,
                Severity.CRITICAL,
                f"`{name}()` runs a shell command built from a string.",
                "Use `subprocess.run([...])` with an argument list; it does not invoke a shell.",
                node.lineno,
            )
        elif name in {"subprocess.run", "subprocess.Popen", "subprocess.call"}:
            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    self._add(
                        Dimension.SECURITY,
                        Severity.CRITICAL,
                        "`shell=True` allows command injection if any part of the command "
                        "comes from input.",
                        "Pass a list of arguments and leave `shell` at its default.",
                        node.lineno,
                    )
        elif name == "open" and not self._inside_with(node):
            self._add(
                Dimension.CORRECTNESS,
                Severity.MAJOR,
                "File opened outside a `with` block.",
                "`with open(...) as f:` closes the file even when an exception is raised.",
                node.lineno,
            )
        self.generic_visit(node)

    def _inside_with(self, node: ast.Call) -> bool:
        """Whether this ``open()`` call is the context expression of a ``with``."""
        return node.lineno in self._with_context_lines

    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        """Flag identity comparisons against literals."""
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            # `is` is correct for None and the booleans; against any other
            # literal it is comparing identity where value was meant.
            if (
                isinstance(op, ast.Is | ast.IsNot)
                and isinstance(comparator, ast.Constant)
                and comparator.value is not None
                and not isinstance(comparator.value, bool)
            ):
                self._add(
                    Dimension.CORRECTNESS,
                    Severity.MAJOR,
                    "`is` compares identity, not value.",
                    "Use `==` for values. `is` is only correct for `None`, `True`, `False` "
                    "and sentinel objects.",
                    node.lineno,
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        """Flag single-character and non-descriptive names, and hardcoded secrets."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._check_name(target.id, node.lineno)
                self._check_secret(target.id, node)
        self.generic_visit(node)

    def _check_name(self, name: str, line: int) -> None:
        if name in {"l", "O", "I"}:
            self._add(
                Dimension.NAMING,
                Severity.MINOR,
                f"`{name}` is easy to misread as a digit.",
                "PEP 8 explicitly discourages these three names.",
                line,
            )
        elif re.fullmatch(r"(data|temp|tmp|result|value|thing|stuff|foo|x1)\d*", name):
            self._add(
                Dimension.NAMING,
                Severity.INFO,
                f"`{name}` does not say what it holds.",
                "Name it after the thing it contains, e.g. `pending_orders`.",
                line,
            )

    def _check_secret(self, name: str, node: ast.Assign) -> None:
        if not re.search(r"(password|secret|token|api_?key|passwd)", name, re.IGNORECASE):
            return
        # A very short literal is more likely a placeholder than a real secret.
        if (
            isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and len(node.value.value) > 3
        ):
            self._add(
                Dimension.SECURITY,
                Severity.CRITICAL,
                f"`{name}` looks like a hardcoded secret.",
                "Read it from an environment variable or a secrets manager. Anything in "
                "source control is public to everyone with repository access.",
                node.lineno,
            )

    def visit_BinOp(self, node: ast.BinOp) -> None:  # noqa: N802
        """Flag SQL built by string concatenation."""
        if isinstance(node.op, ast.Add | ast.Mod):
            rendered = ast.unparse(node) if hasattr(ast, "unparse") else ""
            if re.search(r"(SELECT|INSERT|UPDATE|DELETE)\s", rendered, re.IGNORECASE):
                self._add(
                    Dimension.SECURITY,
                    Severity.CRITICAL,
                    "SQL is being assembled by string concatenation.",
                    "Use parameterised queries: `cursor.execute('... WHERE id = ?', (id,))`. "
                    "String building is how SQL injection happens.",
                    node.lineno,
                )
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:  # noqa: N802
        """Flag SQL built with f-strings."""
        rendered = ast.unparse(node) if hasattr(ast, "unparse") else ""
        if re.search(r"(SELECT|INSERT|UPDATE|DELETE)\s", rendered, re.IGNORECASE) and any(
            isinstance(value, ast.FormattedValue) for value in node.values
        ):
            self._add(
                Dimension.SECURITY,
                Severity.CRITICAL,
                "SQL is being built with an f-string.",
                "Interpolated values are not escaped. Use query parameters instead.",
                node.lineno,
            )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        """Flag ``range(len(...))`` C-style iteration."""
        if (
            isinstance(node.iter, ast.Call)
            and _call_name(node.iter) == "range"
            and node.iter.args
            and isinstance(node.iter.args[0], ast.Call)
            and _call_name(node.iter.args[0]) == "len"
        ):
            self._add(
                Dimension.READABILITY,
                Severity.MINOR,
                "`for i in range(len(seq))` is a C-style loop.",
                "Iterate directly (`for item in seq`) or use `enumerate(seq)` when you need "
                "the index too.",
                node.lineno,
            )
        for child in ast.walk(node):
            if (
                isinstance(child, ast.AugAssign)
                and isinstance(child.op, ast.Add)
                and isinstance(child.value, ast.List)
            ):
                self._add(
                    Dimension.PERFORMANCE,
                    Severity.MINOR,
                    "Building a list with `+=` inside a loop copies on every iteration.",
                    "Use `list.append(item)`, or a comprehension, for linear rather than "
                    "quadratic cost.",
                    child.lineno,
                )
        self.generic_visit(node)


def _call_name(node: ast.Call) -> str:
    """Best-effort dotted name of a call target."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = [func.attr]
        current: ast.expr = func.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _cyclomatic_complexity(node: ast.AST) -> int:
    """Count decision points plus one."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, ast.If | ast.For | ast.While | ast.ExceptHandler | ast.With):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, ast.IfExp | ast.Assert):
            complexity += 1
        elif isinstance(child, ast.comprehension):
            complexity += 1 + len(child.ifs)
    return complexity


def _max_nesting(node: ast.AST, depth: int = 0) -> int:
    """Deepest block nesting under ``node``."""
    nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)
    deepest = depth
    for child in ast.iter_child_nodes(node):
        child_depth = depth + 1 if isinstance(child, nesting_nodes) else depth
        deepest = max(deepest, _max_nesting(child, child_depth))
    return deepest


def _line_level_findings(filename: str, source: str) -> list[Finding]:
    """PEP 8 checks that operate on raw text rather than the AST."""
    findings: list[Finding] = []
    for number, line in enumerate(source.splitlines(), start=1):
        if len(line) > MAX_LINE_LENGTH:
            findings.append(
                Finding(
                    Dimension.PEP8,
                    Severity.MINOR,
                    f"Line is {len(line)} characters (limit {MAX_LINE_LENGTH}).",
                    "Wrap it. Long lines force horizontal scrolling in reviews and diffs.",
                    filename,
                    number,
                )
            )
        if "\t" in line:
            findings.append(
                Finding(
                    Dimension.PEP8,
                    Severity.MINOR,
                    "Tab character used for indentation.",
                    "PEP 8 specifies 4 spaces. Mixing tabs and spaces is a TabError waiting "
                    "to happen.",
                    filename,
                    number,
                )
            )
        if line.rstrip() != line and line.strip():
            findings.append(
                Finding(
                    Dimension.PEP8,
                    Severity.INFO,
                    "Trailing whitespace.",
                    "Strip it; most editors can do this on save.",
                    filename,
                    number,
                )
            )
    return findings


def _testability_findings(filename: str, source: str, tree: ast.Module) -> list[Finding]:
    """Assess whether the code could be tested without being rewritten."""
    findings: list[Finding] = []
    top_level_statements = [
        node
        for node in tree.body
        if not isinstance(
            node,
            ast.FunctionDef
            | ast.AsyncFunctionDef
            | ast.ClassDef
            | ast.Import
            | ast.ImportFrom
            | ast.Assign
            | ast.AnnAssign
            | ast.Expr,
        )
    ]
    has_main_guard = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in tree.body
    )
    side_effect_calls = [
        node
        for node in tree.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and _call_name(node.value) not in {"print"}
    ]
    if (top_level_statements or side_effect_calls) and not has_main_guard:
        findings.append(
            Finding(
                Dimension.TESTABILITY,
                Severity.MAJOR,
                "Work happens at import time.",
                "Move it into functions and guard the entrypoint with "
                "`if __name__ == '__main__':`. Otherwise importing the module for a test "
                "runs the program.",
                filename,
                1,
            )
        )
    if "input(" in source and not has_main_guard:
        findings.append(
            Finding(
                Dimension.TESTABILITY,
                Severity.MINOR,
                "`input()` is called outside a main guard.",
                "Take values as function parameters and read input only in the entrypoint; "
                "then the logic can be tested without a keyboard.",
                filename,
                None,
            )
        )
    return findings


def review_files(files: dict[str, str]) -> ReviewResult:
    """Review every Python file in ``files`` and produce an aggregate result."""
    findings: list[Finding] = []
    documented = annotated = functions = 0
    module_docstrings = python_files = 0

    for filename, source in sorted(files.items()):
        if not filename.endswith(".py") or not source.strip():
            continue
        python_files += 1
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as exc:
            findings.append(
                Finding(
                    Dimension.CORRECTNESS,
                    Severity.CRITICAL,
                    f"{filename} does not parse: {exc.msg}",
                    "Fix the syntax error before anything else — nothing runs until it parses.",
                    filename,
                    exc.lineno,
                )
            )
            continue

        analyzer = _Analyzer(filename, source)
        analyzer.visit(tree)
        findings.extend(analyzer.findings)
        findings.extend(_line_level_findings(filename, source))
        findings.extend(_testability_findings(filename, source, tree))

        functions += analyzer.function_count
        documented += analyzer.documented_functions
        annotated += analyzer.annotated_functions
        module_docstrings += int(analyzer.has_module_docstring)

    if python_files == 0:
        return ReviewResult(
            findings=[],
            dimension_scores={},
            overall_score=0.0,
            summary="No Python source was submitted to review.",
        )

    scores = _score_dimensions(findings)
    overall = _overall_score(scores, findings)
    strengths = _identify_strengths(
        findings, functions, documented, annotated, module_docstrings, python_files
    )
    return ReviewResult(
        findings=sorted(
            findings,
            key=lambda f: (list(Severity).index(f.severity), f.file, f.line or 0),
        ),
        dimension_scores=scores,
        overall_score=overall,
        summary=_summarise(findings, overall),
        strengths=strengths,
    )


def _score_dimensions(findings: list[Finding]) -> dict[str, float]:
    """Start every dimension at 1.0 and subtract the cost of its findings."""
    scores = {dimension.value: 1.0 for dimension in Dimension}
    for finding in findings:
        scores[finding.dimension.value] = max(
            0.0, scores[finding.dimension.value] - _SEVERITY_COST[finding.severity]
        )
    return {key: round(value, 4) for key, value in scores.items()}


def _overall_score(scores: dict[str, float], findings: list[Finding]) -> float:
    """Combine the dimension scores into one headline figure.

    A plain mean across all eleven dimensions is misleading: code with four
    critical defects concentrated in three dimensions still scored 87%, because
    the eight untouched dimensions averaged the damage away — and that number
    contradicted the engine's own "request changes" verdict.

    So the mean is multiplied by a severity penalty driven by the *count* of
    serious findings. The reasoning a reviewer would apply: one critical defect
    means this cannot ship regardless of how tidy the rest is.
    """
    mean = sum(scores.values()) / len(scores)
    criticals = sum(1 for f in findings if f.severity is Severity.CRITICAL)
    majors = sum(1 for f in findings if f.severity is Severity.MAJOR)
    penalty = 1.0 - min(0.75, 0.22 * criticals + 0.07 * majors)
    return round(mean * penalty, 4)


def _identify_strengths(
    findings: list[Finding],
    functions: int,
    documented: int,
    annotated: int,
    module_docstrings: int,
    python_files: int,
) -> list[str]:
    """Say what the submission does well — a review that only criticises is not useful."""
    strengths: list[str] = []
    by_dimension = {finding.dimension for finding in findings}
    if Dimension.SECURITY not in by_dimension:
        strengths.append(
            "No unsafe patterns found — no shell injection, eval or hardcoded secrets."
        )
    if Dimension.ERROR_HANDLING not in by_dimension:
        strengths.append("Exception handling is specific rather than catch-all.")
    if functions and documented == functions:
        strengths.append("Every function is documented.")
    if functions and annotated == functions:
        strengths.append("Every function is fully type-annotated.")
    if module_docstrings == python_files:
        strengths.append("Every module has a docstring explaining its purpose.")
    if Dimension.COMPLEXITY not in by_dimension and functions:
        strengths.append("Functions are short and their branching stays readable.")
    return strengths


def _summarise(findings: list[Finding], overall: float) -> str:
    """One paragraph in the voice of a senior reviewer."""
    critical = sum(1 for f in findings if f.severity is Severity.CRITICAL)
    major = sum(1 for f in findings if f.severity is Severity.MAJOR)
    minor = sum(1 for f in findings if f.severity is Severity.MINOR)

    if critical:
        verdict = (
            f"**Request changes.** {critical} critical issue"
            f"{'s' if critical != 1 else ''} would cause incorrect behaviour or a security "
            "problem in production. Address those first; the rest can follow."
        )
    elif major >= 3:
        verdict = (
            f"**Request changes.** No showstoppers, but {major} issues will make this hard "
            "to maintain. Worth fixing before merge."
        )
    elif major or minor > 5:
        verdict = (
            "**Approve with comments.** The logic holds up. The notes below are about "
            "readability and long-term maintenance."
        )
    else:
        verdict = "**Approve.** Clean, readable and safe. This is the standard to keep."

    return (
        f"{verdict}\n\n"
        f"Overall quality score: **{round(overall * 100)}%** "
        f"({critical} critical, {major} major, {minor} minor)."
    )
