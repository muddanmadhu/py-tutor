"""Project academy content.

The projects deliberately span the guidance fade-out from spec §50:

``calculator-cli``            fully guided — every milestone spelled out
``expense-tracker-cli``       partially guided — structure given, logic yours
``file-processing-platform``  requirements only — you design it
``enterprise-automation-service``  independent capstone — a business brief and
                              an engineering rubric, nothing else
"""

from __future__ import annotations

from app.content.schema import ProjectSpec
from app.models.enums import GuidanceLevel, SkillLevel

STANDARD_RUBRIC = (
    {
        "key": "correctness",
        "label": "Correctness",
        "weight": 3.0,
        "description": "Does it do what the requirements say, including the edge cases?",
    },
    {
        "key": "architecture",
        "label": "Architecture",
        "weight": 2.0,
        "description": "Are concerns separated into modules with clear responsibilities?",
    },
    {
        "key": "testing",
        "label": "Testing",
        "weight": 2.5,
        "description": "Is there a test suite, and does it cover the behaviour that matters?",
    },
    {
        "key": "error_handling",
        "label": "Error handling",
        "weight": 2.0,
        "description": "Are failures anticipated, specific and recoverable?",
    },
    {
        "key": "readability",
        "label": "Readability",
        "weight": 1.5,
        "description": "Naming, docstrings, function size, nesting.",
    },
    {
        "key": "logging",
        "label": "Logging",
        "weight": 1.0,
        "description": "Can you tell what happened from the logs alone?",
    },
    {
        "key": "security",
        "label": "Security",
        "weight": 2.0,
        "description": "Secrets, injection, input validation, safe file handling.",
    },
    {
        "key": "documentation",
        "label": "Documentation",
        "weight": 1.0,
        "description": "Can someone else run and maintain this?",
    },
)

ENTERPRISE_RUBRIC = STANDARD_RUBRIC + (
    {
        "key": "performance",
        "label": "Performance",
        "weight": 1.5,
        "description": "Sensible data structures, no accidental quadratic behaviour, "
        "bounded resource use.",
    },
    {
        "key": "maintainability",
        "label": "Maintainability",
        "weight": 1.5,
        "description": "Could a new engineer add a feature next month without a rewrite?",
    },
    {
        "key": "deployment",
        "label": "Deployment",
        "weight": 1.5,
        "description": "Dependency manifest, containerisation, configuration by environment.",
    },
)


CALCULATOR = ProjectSpec(
    slug="calculator-cli",
    title="Project 1 — Command-Line Calculator",
    tagline="Your first complete program: parse input, compute, handle errors, exit cleanly.",
    level=SkillLevel.BEGINNER,
    guidance=GuidanceLevel.FULLY_GUIDED,
    estimated_hours=2,
    xp_reward=150,
    concepts=("functions", "conditionals", "exceptions", "cli-design"),
    requirements="""\
## Brief

Build a calculator that evaluates a single expression given as arguments.

```
$ python main.py 12 + 30
42
$ python main.py 10 / 0
error: cannot divide by zero
```

## Functional requirements

1. Support `+`, `-`, `*`, `/`
2. Accept integers and decimals
3. Print the result with no trailing `.0` for whole numbers (`42`, not `42.0`)
4. Division by zero prints `error: cannot divide by zero` and exits with code 1
5. An unknown operator prints `error: unknown operator: <op>` and exits with 1
6. Non-numeric input prints `error: not a number: <value>` and exits with 1
7. Wrong argument count prints a usage line and exits with code 2

## Non-functional requirements

* Calculation logic lives in a function that takes numbers and returns a number
  — it must be testable without touching `sys.argv`
* A test suite covering every operator, every error path and the boundaries
* No bare `except`
""",
    architecture_notes="""\
Two layers, and the separation is the whole point:

```
main.py
├── calculate(left, operator, right) -> float     pure: no I/O, fully testable
└── main(argv) -> int                             parses, formats, returns exit code
```

`main(argv=None)` taking its arguments makes the CLI itself testable:
`assert main(["1", "+", "1"]) == 0`. Reading `sys.argv` inside the logic would
make that impossible.
""",
    suggested_structure="""\
calculator/
├── main.py            calculate() and main()
├── test_calculator.py the suite
└── README.md          how to run it
""",
    milestones=(
        {
            "key": "calculate",
            "title": "Write `calculate(left, operator, right)`",
            "detail": "Four operators. Raise ZeroDivisionError for division by zero and "
            "ValueError for an unknown operator. No printing.",
        },
        {
            "key": "tests-happy",
            "title": "Test the happy path",
            "detail": "One test per operator, plus a decimal case.",
        },
        {
            "key": "tests-errors",
            "title": "Test the error paths",
            "detail": "pytest.raises for divide-by-zero and unknown operator.",
        },
        {
            "key": "cli",
            "title": "Write `main(argv)`",
            "detail": "Parse three arguments, call calculate, print, return an exit code.",
        },
        {
            "key": "formatting",
            "title": "Format the output",
            "detail": "Whole results print without a decimal point.",
        },
        {
            "key": "readme",
            "title": "Write the README",
            "detail": "What it does, how to run it, how to run the tests.",
        },
    ),
    starter_files={
        "main.py": '''\
"""A command-line calculator."""

import sys


def calculate(left: float, operator: str, right: float) -> float:
    """Apply `operator` to two numbers.

    Raises
    ------
    ZeroDivisionError
        On division by zero.
    ValueError
        If the operator is not recognised.
    """
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """Run the calculator. Returns the process exit code."""
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
''',
        "test_calculator.py": '''\
"""Tests for the calculator."""

import pytest

from main import calculate, main


def test_addition():
    assert calculate(2, "+", 3) == 5


# Add the rest.
''',
        "README.md": "# Calculator\n\nTODO: describe how to run this.\n",
    },
    acceptance_tests={
        "test_acceptance_calculator.py": '''\
"""Acceptance tests for the calculator project."""

import pytest

from main import calculate, main


class TestCalculate:
    def test_addition(self):
        assert calculate(2, "+", 3) == 5

    def test_subtraction(self):
        assert calculate(10, "-", 4) == 6

    def test_multiplication(self):
        assert calculate(3, "*", 7) == 21

    def test_division(self):
        assert calculate(10, "/", 4) == 2.5

    def test_division_by_zero_raises(self):
        with pytest.raises(ZeroDivisionError):
            calculate(1, "/", 0)

    def test_unknown_operator_raises(self):
        with pytest.raises(ValueError):
            calculate(1, "^", 2)


class TestCli:
    def test_success_exit_code(self, capsys):
        assert main(["12", "+", "30"]) == 0
        assert capsys.readouterr().out.strip() == "42"

    def test_decimal_result(self, capsys):
        assert main(["10", "/", "4"]) == 0
        assert capsys.readouterr().out.strip() == "2.5"

    def test_divide_by_zero_exit_code(self, capsys):
        assert main(["1", "/", "0"]) == 1
        assert "cannot divide by zero" in capsys.readouterr().out.lower()

    def test_bad_number_exit_code(self, capsys):
        assert main(["x", "+", "1"]) == 1

    def test_unknown_operator_exit_code(self, capsys):
        assert main(["1", "^", "2"]) == 1

    def test_wrong_argument_count(self, capsys):
        assert main(["1", "+"]) == 2
'''
    },
    rubric=STANDARD_RUBRIC[:6],
)


EXPENSE_TRACKER = ProjectSpec(
    slug="expense-tracker-cli",
    title="Project 2 — Expense Tracker",
    tagline="Persistent state, JSON storage, reporting and a real CLI.",
    level=SkillLevel.INTERMEDIATE,
    guidance=GuidanceLevel.PARTIALLY_GUIDED,
    estimated_hours=5,
    xp_reward=300,
    concepts=("classes", "file-io", "json-data", "cli-design", "unit-testing", "exceptions"),
    prerequisites=("calculator-cli",),
    requirements="""\
## Brief

A command-line expense tracker that survives restarts.

```
$ python main.py add --amount 12.50 --category food --note "lunch"
Added expense #1

$ python main.py list --category food
#1  2026-09-06  food      12.50  lunch

$ python main.py report --month 2026-09
food        12.50
transport   40.00
────────────────
TOTAL       52.50
```

## Functional requirements

1. `add` — amount (positive), category, optional note; assigns a sequential id
2. `list` — all expenses, optionally filtered by `--category` or `--month`
3. `report` — totals per category for a month, plus a grand total
4. `delete --id N` — remove an expense; unknown id is an error, not a crash
5. Data persists to `expenses.json` between runs
6. A corrupt or missing data file must not crash the program: report it and
   start from empty

## Non-functional requirements

* Storage is behind an interface, so the tests never touch the real file
* Money is handled without float drift — store integer pence, or use `Decimal`
* Every command returns a meaningful exit code
* At least 12 tests, including the corrupt-file case
* A `--dry-run` flag on any command that writes
""",
    architecture_notes="""\
```
main.py          argument parsing, exit codes, output formatting
storage.py       load/save JSON; the only module that touches the filesystem
models.py        the Expense dataclass and its validation
reporting.py     pure aggregation functions over a list of expenses
```

The dependency arrow points one way: `main` knows about the others; none of them
knows about `main`. That is what makes `reporting.py` testable with a literal
list of expenses and no I/O at all.

On money: `12.50` as a float is not exactly 12.50, and summing thousands of them
drifts. Store `1250` pence as an int and format on the way out.
""",
    suggested_structure="""\
expense_tracker/
├── main.py
├── models.py
├── storage.py
├── reporting.py
├── tests/
│   ├── test_models.py
│   ├── test_storage.py
│   └── test_reporting.py
└── README.md
""",
    milestones=(
        {
            "key": "model",
            "title": "The Expense model",
            "detail": "A dataclass with validation. Amount stored as integer pence.",
        },
        {
            "key": "storage",
            "title": "JSON storage",
            "detail": "load() and save(). Handle a missing file and invalid JSON.",
        },
        {
            "key": "commands",
            "title": "add / list / delete",
            "detail": "Each returns an exit code; none prints from inside the logic.",
        },
        {
            "key": "reporting",
            "title": "Monthly report",
            "detail": "Pure functions over a list of expenses — no file access.",
        },
        {
            "key": "cli",
            "title": "argparse subcommands",
            "detail": "Sub-parsers per command, plus --dry-run.",
        },
        {
            "key": "tests",
            "title": "Test suite",
            "detail": "Use tmp_path for storage tests. Include the corrupt-file case.",
        },
        {"key": "docs", "title": "README", "detail": "Install, usage, examples, how to test."},
    ),
    starter_files={
        "models.py": '''\
"""Domain model for an expense."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Expense:
    """A single recorded expense. Amount is stored in pence to avoid float drift."""

    id: int
    date: str          # ISO 8601, e.g. "2026-09-06"
    category: str
    amount_pence: int
    note: str = ""
''',
        "storage.py": '"""JSON persistence. The only module that touches the filesystem."""\n',
        "reporting.py": '"""Pure aggregation over expenses. No I/O in this module."""\n',
        "main.py": '"""CLI entry point."""\n',
        "README.md": "# Expense Tracker\n",
    },
    acceptance_tests={
        "test_acceptance_expenses.py": '''\
"""Acceptance tests: these check the contract, not your internal design."""

import json
from pathlib import Path

import pytest


def test_expense_model_exists():
    from models import Expense

    expense = Expense(id=1, date="2026-09-06", category="food", amount_pence=1250)
    assert expense.amount_pence == 1250


def test_storage_roundtrip(tmp_path):
    import storage

    path = tmp_path / "expenses.json"
    records = [{"id": 1, "date": "2026-09-06", "category": "food",
                "amount_pence": 1250, "note": "lunch"}]
    storage.save(path, records)
    assert storage.load(path) == records


def test_storage_handles_missing_file(tmp_path):
    import storage

    assert storage.load(tmp_path / "nope.json") == []


def test_storage_handles_corrupt_file(tmp_path):
    import storage

    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert storage.load(path) == [], "a corrupt file must not crash the program"


def test_report_totals_by_category():
    import reporting

    expenses = [
        {"category": "food", "amount_pence": 1250, "date": "2026-09-01"},
        {"category": "food", "amount_pence": 750, "date": "2026-09-02"},
        {"category": "transport", "amount_pence": 4000, "date": "2026-09-03"},
    ]
    totals = reporting.totals_by_category(expenses)
    assert totals["food"] == 2000
    assert totals["transport"] == 4000


def test_report_filters_by_month():
    import reporting

    expenses = [
        {"category": "food", "amount_pence": 100, "date": "2026-09-01"},
        {"category": "food", "amount_pence": 200, "date": "2026-08-01"},
    ]
    september = reporting.filter_by_month(expenses, "2026-09")
    assert len(september) == 1


def test_cli_add_and_list(tmp_path, monkeypatch, capsys):
    import main

    monkeypatch.chdir(tmp_path)
    assert main.main(["add", "--amount", "12.50", "--category", "food"]) == 0
    assert main.main(["list"]) == 0
    assert "food" in capsys.readouterr().out


def test_cli_rejects_negative_amount(tmp_path, monkeypatch):
    import main

    monkeypatch.chdir(tmp_path)
    assert main.main(["add", "--amount", "-5", "--category", "food"]) != 0
'''
    },
    rubric=STANDARD_RUBRIC,
)


FILE_PLATFORM = ProjectSpec(
    slug="file-processing-platform",
    title="Project 3 — Enterprise File Processing Platform",
    tagline="Requirements only. You design the architecture.",
    level=SkillLevel.PROFESSIONAL,
    guidance=GuidanceLevel.REQUIREMENTS_ONLY,
    estimated_hours=12,
    xp_reward=600,
    concepts=(
        "automation-design",
        "file-io",
        "csv-data",
        "json-data",
        "logging",
        "exceptions",
        "unit-testing",
        "cli-design",
        "security-basics",
        "regex",
    ),
    prerequisites=("expense-tracker-cli",),
    requirements="""\
## Business requirement

*Operations receive supplier files by SFTP into a landing directory. Today three
people open each file, check it, retype the totals into a spreadsheet and email
the result. It takes four hours a day and mistakes reach customers.*

Build a platform that processes these files automatically.

### Inputs

* CSV and JSON files arrive in an `inbox/` directory at unpredictable times
* Files vary in size from 1 KB to 500 MB
* Some are malformed; some are duplicates of a file already processed
* Filenames follow `{supplier}_{YYYYMMDD}_{sequence}.{csv|json}`

### Required behaviour

1. Discover and process every unprocessed file in `inbox/`
2. Validate each file against a per-supplier schema; reject non-conforming
   files without losing them
3. Transform valid records into a canonical output format
4. Write results to `output/`, move inputs to `archive/`, and failures to
   `quarantine/` with a `.error.json` explaining why
5. Produce a run summary: files processed, records written, records rejected,
   duration
6. Re-running must not reprocess, duplicate or lose anything
7. A 500 MB file must not exhaust memory
8. One bad file must not stop the run
9. Every run has a correlation id present on every log line
10. `--dry-run` reports what would happen and changes nothing

### Constraints

* Standard library only (no pandas)
* Peak memory must stay under 200 MB regardless of input size
* Test coverage of the core logic at 80% or above
* No secrets or paths hardcoded — configuration comes from the environment

## What you are being assessed on

Not whether it works on the happy path. Whether it is safe to run unattended
against real supplier data at 2am, and whether the person on call can tell what
happened from the logs.
""",
    architecture_notes="""\
No structure is prescribed. Some decisions you will have to make, and should be
able to justify:

* **Streaming vs loading.** Requirement 7 rules out `json.load` on a 500 MB
  file. What is your strategy — line-delimited JSON, an incremental parser, or a
  documented size limit with a clear failure?
* **Idempotency mechanism.** A ledger file, a hash of the content, or the
  presence of the file in `archive/`? Each has a different failure mode.
* **Where validation lives.** Per-supplier schemas as data, or as code?
* **Atomicity.** Requirement 6 means a crash mid-write must not leave a
  half-written output that the next run treats as complete.
""",
    suggested_structure="",
    milestones=(),
    starter_files={
        "README.md": "# File Processing Platform\n\nDocument your design decisions here "
        "before you write code. The rubric rewards a defensible architecture.\n",
    },
    acceptance_tests={
        "test_acceptance_platform.py": '''\
"""Contract-level acceptance tests.

These deliberately test the *observable contract* from the requirements rather
than any particular design, because the design is yours.
"""

import importlib
import json
from pathlib import Path

import pytest

processor = pytest.importorskip(
    "processor", reason="expose a `processor` module with a `run(...)` entry point"
)


def _make_inbox(tmp_path, files):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, content in files.items():
        (inbox / name).write_text(content, encoding="utf-8")
    for folder in ("output", "archive", "quarantine"):
        (tmp_path / folder).mkdir(exist_ok=True)
    return tmp_path


GOOD_CSV = "order_id,amount,currency\\n1,10.00,GBP\\n2,20.00,GBP\\n"
BAD_CSV = "this is not a csv at all\\n\\x00\\n"


def test_processes_a_valid_file(tmp_path):
    root = _make_inbox(tmp_path, {"acme_20260906_001.csv": GOOD_CSV})
    summary = processor.run(root)
    assert summary["files_processed"] >= 1
    assert summary["records_written"] == 2
    assert not list((root / "inbox").glob("*.csv")), "input should be moved out of inbox"
    assert list((root / "archive").glob("*.csv")), "input should land in archive"


def test_quarantines_a_bad_file(tmp_path):
    root = _make_inbox(tmp_path, {"acme_20260906_002.csv": BAD_CSV})
    summary = processor.run(root)
    assert summary["files_failed"] >= 1
    quarantined = list((root / "quarantine").glob("*"))
    assert quarantined, "a rejected file must be preserved in quarantine"
    assert any(p.name.endswith(".error.json") for p in quarantined), (
        "quarantine must include an explanation of why the file was rejected"
    )


def test_one_bad_file_does_not_stop_the_run(tmp_path):
    root = _make_inbox(
        tmp_path,
        {"acme_20260906_003.csv": BAD_CSV, "acme_20260906_004.csv": GOOD_CSV},
    )
    summary = processor.run(root)
    assert summary["records_written"] == 2
    assert summary["files_failed"] >= 1


def test_rerun_is_idempotent(tmp_path):
    root = _make_inbox(tmp_path, {"acme_20260906_005.csv": GOOD_CSV})
    first = processor.run(root)
    second = processor.run(root)
    assert first["records_written"] == 2
    assert second["records_written"] == 0, "a re-run must not reprocess"


def test_dry_run_changes_nothing(tmp_path):
    root = _make_inbox(tmp_path, {"acme_20260906_006.csv": GOOD_CSV})
    processor.run(root, dry_run=True)
    assert list((root / "inbox").glob("*.csv")), "dry run must not move the input"
    assert not list((root / "output").glob("*")), "dry run must not write output"


def test_summary_shape(tmp_path):
    root = _make_inbox(tmp_path, {"acme_20260906_007.csv": GOOD_CSV})
    summary = processor.run(root)
    for key in ("files_processed", "files_failed", "records_written",
                "records_rejected", "duration_seconds", "correlation_id"):
        assert key in summary, f"the run summary must include {key!r}"
'''
    },
    rubric=ENTERPRISE_RUBRIC,
)


CAPSTONE = ProjectSpec(
    slug="enterprise-automation-service",
    title="Capstone — Enterprise Automation Service",
    tagline="A business requirement and an engineering rubric. Everything else is yours.",
    level=SkillLevel.ENGINEERING,
    guidance=GuidanceLevel.INDEPENDENT,
    estimated_hours=30,
    xp_reward=1500,
    is_capstone=True,
    concepts=(
        "rest-services",
        "databases",
        "api-clients",
        "automation-design",
        "logging",
        "test-design",
        "security-basics",
        "performance",
        "concurrency",
    ),
    prerequisites=("file-processing-platform",),
    requirements="""\
## Requirement document — Order Reconciliation Service

**From:** Head of Operations
**To:** Engineering
**Priority:** High

### Background

We take orders through a third-party marketplace and fulfil them from our own
warehouse. Twice this quarter we have shipped orders that were already
cancelled, and once we failed to ship an order that was paid for. Both were
found by a customer, not by us.

We need a service that reconciles the marketplace against the warehouse
continuously and surfaces every discrepancy before a customer does.

### What it must do

1. **Ingest** orders from the marketplace REST API
   * paginated, token-authenticated, rate-limited to 100 requests/minute
   * the API is unreliable: expect timeouts and 5xx
   * pull incrementally — do not re-fetch the whole history every run

2. **Reconcile** each order against warehouse state held in PostgreSQL
   * classify each as: matched, missing-in-warehouse, cancelled-but-shipped,
     quantity-mismatch, or price-mismatch

3. **Store** every reconciliation run and its results
   * a run is auditable months later: what was compared, and what was decided

4. **Expose** an HTTP API
   * `GET  /health` and `GET  /ready`
   * `GET  /api/runs` — paginated history
   * `GET  /api/runs/{id}/discrepancies` — filterable by type
   * `POST /api/runs` — trigger a run (authenticated)
   * `GET  /api/discrepancies/{id}` — one discrepancy in detail

5. **Notify** when discrepancies of type `cancelled-but-shipped` appear
   * write to a notification table; sending is out of scope

6. **Operate** unattended
   * structured logs with a correlation id per run and per request
   * metrics: run duration, orders compared, discrepancies by type
   * safe to re-run; a crash mid-run must not corrupt the record

### Non-functional requirements

| Area | Requirement |
| --- | --- |
| Correctness | A reconciliation run is atomic: it either records a complete result or none |
| Performance | 50,000 orders reconciled in under 5 minutes |
| Reliability | Marketplace API failures are retried with backoff; a total outage fails the run cleanly, without partial state |
| Security | Token from the environment; no secrets in logs; parameterised SQL; authenticated write endpoints; validated input |
| Testing | Unit tests for reconciliation logic; integration tests against a real database; the marketplace API stubbed, not mocked away entirely |
| Operations | Dockerfile, docker-compose for local development, database migrations, a README a new engineer can follow |
| Observability | A failed run can be diagnosed from the logs alone |

### Out of scope

Front-end, real email delivery, multi-tenancy, Kubernetes manifests.

### Deliverables

1. Working source
2. `README.md` — what it is, how to run it, how to test it
3. `ARCHITECTURE.md` — your design and, importantly, the decisions you rejected
   and why
4. Test suite with coverage reported
5. `Dockerfile` and `docker-compose.yml`
6. Database migrations

### How this is assessed

Against the professional engineering rubric. The bar is not "it runs" — it is
*would a senior engineer approve this pull request?* Specifically:

* Is the reconciliation logic pure and unit-tested, or tangled with I/O?
* Is a partially-failed run distinguishable from a successful one?
* Could someone else operate this at 3am from the logs and the README?
* Is there any way a marketplace outage corrupts stored state?
* Are the security requirements met, or merely mentioned?
""",
    architecture_notes="""\
You are being assessed partly on your reasoning, so record it. `ARCHITECTURE.md`
should answer at least:

* Where is the boundary between fetching, reconciling and persisting — and how
  did you make the reconciliation logic testable without a database or a
  network?
* How does incremental ingestion work, and what happens if a watermark is lost?
* What is the transaction boundary for a run? What does a crash at each stage
  leave behind?
* How do you get 50,000 orders reconciled in 5 minutes — concurrency, batching,
  indexes, or all three? What did you measure?
* What did you *not* build, and why?

A design you can defend beats a design that is merely large.
""",
    suggested_structure="",
    milestones=(),
    starter_files={
        "ARCHITECTURE.md": "# Architecture\n\n## Context\n\n## Decisions\n\n"
        "### Decision: ...\n\n**Options considered:**\n\n**Chosen:**\n\n**Why:**\n\n"
        "**Rejected because:**\n\n## Data model\n\n## Failure modes\n",
        "README.md": "# Order Reconciliation Service\n",
    },
    acceptance_tests={
        "test_acceptance_capstone.py": '''\
"""Capstone acceptance checks.

The capstone is scored primarily by the engineering rubric and by human review.
These automated checks verify only the structural claims — that the deliverables
exist and that the reconciliation logic is separable from its I/O, which is the
single strongest predictor of whether the rest of the requirements were taken
seriously.
"""

from pathlib import Path

import pytest


def test_readme_exists_and_is_substantial():
    readme = Path("README.md")
    assert readme.exists(), "README.md is a required deliverable"
    assert len(readme.read_text(encoding="utf-8")) > 500, (
        "the README must explain what this is, how to run it and how to test it"
    )


def test_architecture_document_records_decisions():
    doc = Path("ARCHITECTURE.md")
    assert doc.exists(), "ARCHITECTURE.md is a required deliverable"
    text = doc.read_text(encoding="utf-8").lower()
    assert len(text) > 800, "record your design and the options you rejected"
    assert "decision" in text or "rejected" in text, (
        "the brief asks specifically for the decisions you rejected and why"
    )


def test_dependency_manifest_exists():
    assert Path("requirements.txt").exists() or Path("pyproject.toml").exists(), (
        "declare your dependencies"
    )


def test_dockerfile_exists():
    assert Path("Dockerfile").exists(), "containerisation is a stated requirement"


def test_has_a_test_suite():
    tests = [p for p in Path(".").rglob("test_*.py")
             if not p.name.startswith("test_acceptance")]
    assert tests, "ship a test suite"


def test_reconciliation_logic_is_importable_without_io():
    """Pure logic must be importable without a database or a network.

    If importing your reconciliation module opens a connection, the logic is not
    separable from its I/O and cannot be unit-tested.
    """
    module = pytest.importorskip(
        "reconciliation",
        reason="expose the comparison logic as a `reconciliation` module",
    )
    assert hasattr(module, "reconcile"), (
        "expose a `reconcile(...)` function that compares orders to warehouse "
        "state and returns discrepancies - taking data, not connections"
    )


def test_reconcile_detects_the_required_discrepancy_types():
    module = pytest.importorskip("reconciliation")
    marketplace = [
        {"order_id": "1", "status": "active", "quantity": 2, "price_pence": 1000},
        {"order_id": "2", "status": "cancelled", "quantity": 1, "price_pence": 500},
        {"order_id": "3", "status": "active", "quantity": 5, "price_pence": 100},
    ]
    warehouse = [
        {"order_id": "1", "shipped": False, "quantity": 2, "price_pence": 1000},
        {"order_id": "2", "shipped": True, "quantity": 1, "price_pence": 500},
    ]
    results = module.reconcile(marketplace, warehouse)
    kinds = {getattr(r, "kind", None) or r.get("kind") for r in results}
    assert "cancelled-but-shipped" in kinds
    assert "missing-in-warehouse" in kinds
'''
    },
    rubric=ENTERPRISE_RUBRIC,
)


PROJECTS: tuple[ProjectSpec, ...] = (
    CALCULATOR,
    EXPENSE_TRACKER,
    FILE_PLATFORM,
    CAPSTONE,
)
