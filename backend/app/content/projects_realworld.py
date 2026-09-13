"""Real-world project academy content.

Seven builds modelled on work that actually lands in a sprint: log triage, a
finance report, a resilient API client, invoice reconciliation, an ETL load,
inventory sync between two systems, and an on-call incident report.

They sit between the four original projects in size (4–6 hours each) so the
guidance fade-out has more rungs, and they are deliberately *ordinary* — the kind
of task an engineer is handed in their first year, stated as a business
requirement rather than as an exercise.

One constraint shapes every acceptance test here: the static build runs learner
code under Pyodide, which has no network and no database. So a project that is
"about" HTTP is graded on the logic around HTTP — retries, backoff, pagination,
error classification — with the transport injected by the test. That is also how
this code would be tested in production, which makes the constraint a feature.
"""

from __future__ import annotations

from app.content.projects import ENTERPRISE_RUBRIC, STANDARD_RUBRIC
from app.content.schema import ProjectSpec
from app.models.enums import GuidanceLevel, SkillLevel

# ---------------------------------------------------------------------------
# 1 — Log analyzer
# ---------------------------------------------------------------------------

LOG_ANALYZER = ProjectSpec(
    slug="log-analyzer",
    title="Log Analyzer — Find the Error That Matters",
    tagline="Turn a 200 MB log nobody reads into a one-page summary somebody acts on.",
    level=SkillLevel.INTERMEDIATE,
    guidance=GuidanceLevel.PARTIALLY_GUIDED,
    estimated_hours=4,
    xp_reward=250,
    concepts=("file-io", "regex", "dictionaries", "sorting", "complexity"),
    prerequisites=("expense-tracker-cli",),
    requirements="""\
## The situation

The overnight batch failed. There is a 200 MB log file, the on-call engineer has
fifteen minutes, and "grep ERROR | wc -l" says 48,000 — which is useless, because
they are nearly all the same error repeated.

Build the tool that answers the question actually being asked: **what broke, how
often, and when did it start?**

## Log format

Lines look like this. Anything that does not match is a continuation line
(a traceback, usually) and belongs to the entry above it:

```
2026-09-11T02:14:07Z ERROR  orders.sync   Timeout contacting inventory-svc after 30s
2026-09-11T02:14:07Z INFO   orders.sync   Retrying (1/3)
2026-09-11T02:14:38Z ERROR  orders.sync   Timeout contacting inventory-svc after 30s
```

`TIMESTAMP LEVEL LOGGER MESSAGE` — whitespace-separated, message runs to the end.

## What it must do

1. Parse a log file into entries, attaching continuation lines to their entry.
2. Group errors by a **normalised** message, so that
   `Timeout contacting inventory-svc after 30s` and
   `Timeout contacting inventory-svc after 45s` count as the same problem. Digits
   and quoted strings are the parts that vary.
3. Report, for each group: count, first seen, last seen, the logger, and one
   example message.
4. Order the report by count descending, then first-seen ascending.
5. Handle a file that does not exist, is empty, or contains no parseable lines,
   without a traceback.

## Constraints

- Standard library only.
- The file may be larger than memory: **stream it**, do not `read()` it whole.
- A malformed line must never abort the run — count it and carry on.
""",
    architecture_notes="""\
The interesting decision is normalisation. Replacing every run of digits with `#`
is crude and works surprisingly well; replacing quoted strings too gets you most
of the rest. Resist regex-per-known-error — the tool's value is that it works on
errors nobody has seen yet.

Stream with `for line in file:` rather than `readlines()`. That is the difference
between a tool that works on the real log and one that works on your test
fixture.

Counting wants a dict keyed by the normalised message, holding a small mutable
record. `collections.defaultdict` or `dict.setdefault` both fit; `Counter` alone
does not, because you need first/last seen as well as the count.
""",
    suggested_structure="""\
log_analyzer/
├── main.py           # CLI: path in, report out
├── parsing.py        # line -> LogEntry | None, and continuation handling
├── grouping.py       # normalise() and the aggregation
├── reporting.py      # format the summary
└── tests/
    ├── test_parsing.py
    ├── test_grouping.py
    └── test_reporting.py
""",
    milestones=(
        {
            "key": "parse",
            "title": "Parse one line",
            "detail": "`parse_line(line)` returns an entry or None. Get the None case right "
            "first — it is what makes continuation lines work.",
        },
        {
            "key": "stream",
            "title": "Stream the file into entries",
            "detail": "`parse_lines(lines)` yields entries, appending continuation lines to "
            "the previous entry's message. A generator, so memory stays flat.",
        },
        {
            "key": "normalise",
            "title": "Normalise messages",
            "detail": "`normalise(message)` collapses digits and quoted strings so that "
            "variants of one error group together.",
        },
        {
            "key": "group",
            "title": "Aggregate",
            "detail": "Count, first seen, last seen, logger and an example per group.",
        },
        {
            "key": "report",
            "title": "Order and format",
            "detail": "Count descending, first seen ascending. Then the CLI, and the "
            "not-found and empty-file cases.",
        },
    ),
    starter_files={
        "parsing.py": '''\
"""Turn log lines into entries."""

from dataclasses import dataclass


@dataclass
class LogEntry:
    timestamp: str
    level: str
    logger: str
    message: str


def parse_line(line: str) -> LogEntry | None:
    """Parse one log line, or return None if it is not a log line at all."""
    # Your code here
    ...


def parse_lines(lines) -> list[LogEntry]:
    """Parse an iterable of lines, attaching continuation lines to the entry above."""
    # Your code here
    ...
''',
        "grouping.py": '''\
"""Group similar errors together."""


def normalise(message: str) -> str:
    """Collapse the varying parts of a message so variants group together."""
    # Your code here
    ...


def group_errors(entries) -> list[dict]:
    """Aggregate ERROR entries into groups, ordered for the report."""
    # Your code here
    ...
''',
        "main.py": '''\
"""CLI entry point."""

import sys


def main(argv: list[str]) -> int:
    """Print the report. Return 0 on success, non-zero on a usage or IO error."""
    # Your code here
    ...


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
''',
        "README.md": "# Log Analyzer\n\nHow to run it, and what the report columns mean.\n",
    },
    acceptance_tests={
        "test_acceptance_logs.py": '''\
"""Acceptance tests: the contract, not your internal design."""

import pytest

SAMPLE = [
    "2026-09-11T02:14:07Z ERROR  orders.sync   Timeout contacting inventory-svc after 30s",
    "  File \\"sync.py\\", line 42, in run",
    "    raise TimeoutError(30)",
    "2026-09-11T02:14:09Z INFO   orders.sync   Retrying (1/3)",
    "2026-09-11T02:14:38Z ERROR  orders.sync   Timeout contacting inventory-svc after 45s",
    "2026-09-11T02:15:01Z ERROR  orders.db     Connection pool exhausted",
]


def test_parse_line_returns_fields():
    parsing = pytest.importorskip("parsing", reason="create parsing.py with parse_line()")
    entry = parsing.parse_line(SAMPLE[0])
    assert entry is not None
    assert entry.level == "ERROR"
    assert entry.logger == "orders.sync"
    assert entry.timestamp == "2026-09-11T02:14:07Z"
    assert "Timeout contacting inventory-svc" in entry.message


def test_parse_line_rejects_a_continuation():
    parsing = pytest.importorskip("parsing")
    assert parsing.parse_line(SAMPLE[1]) is None, (
        "a traceback line is not a log line; return None so it can be attached "
        "to the entry above it"
    )
    # Paired with the positive case, so an unimplemented parse_line returning
    # None for everything cannot pass this by accident.
    assert parsing.parse_line(SAMPLE[0]) is not None, "a real log line must parse"


def test_continuation_lines_attach_to_the_previous_entry():
    parsing = pytest.importorskip("parsing")
    entries = list(parsing.parse_lines(SAMPLE))
    assert len(entries) == 4, "four real log lines; the two traceback lines are not entries"
    assert "sync.py" in entries[0].message, "the traceback belongs to the first entry"


def test_normalise_collapses_numbers():
    grouping = pytest.importorskip("grouping", reason="create grouping.py with normalise()")
    a = grouping.normalise("Timeout contacting inventory-svc after 30s")
    b = grouping.normalise("Timeout contacting inventory-svc after 45s")
    assert a == b, "messages differing only in numbers must normalise to the same key"


def test_normalise_keeps_different_errors_apart():
    grouping = pytest.importorskip("grouping")
    a = grouping.normalise("Timeout contacting inventory-svc after 30s")
    b = grouping.normalise("Connection pool exhausted")
    assert a != b


def test_group_errors_counts_and_orders():
    parsing = pytest.importorskip("parsing")
    grouping = pytest.importorskip("grouping")
    groups = grouping.group_errors(list(parsing.parse_lines(SAMPLE)))
    assert len(groups) == 2, "two distinct errors after normalisation"
    assert groups[0]["count"] == 2, "most frequent first"
    assert groups[1]["count"] == 1


def test_group_errors_reports_first_and_last_seen():
    parsing = pytest.importorskip("parsing")
    grouping = pytest.importorskip("grouping")
    top = grouping.group_errors(list(parsing.parse_lines(SAMPLE)))[0]
    assert top["first_seen"] == "2026-09-11T02:14:07Z"
    assert top["last_seen"] == "2026-09-11T02:14:38Z"


def test_group_errors_ignores_non_errors():
    parsing = pytest.importorskip("parsing")
    grouping = pytest.importorskip("grouping")
    groups = grouping.group_errors(list(parsing.parse_lines(SAMPLE)))
    messages = " ".join(str(g) for g in groups)
    assert "Retrying" not in messages, "INFO lines are not errors"


def test_empty_input_is_not_an_error():
    parsing = pytest.importorskip("parsing")
    grouping = pytest.importorskip("grouping")
    assert grouping.group_errors(list(parsing.parse_lines([]))) == []


def test_parse_lines_does_not_build_the_whole_file_eagerly():
    """A generator is what keeps this working on a file larger than memory."""
    import inspect

    parsing = pytest.importorskip("parsing")
    source = inspect.getsource(parsing.parse_lines)
    assert "readlines" not in source, "stream the lines; do not call readlines()"
''',
    },
    rubric=STANDARD_RUBRIC,
)

# ---------------------------------------------------------------------------
# 2 — CSV report engine
# ---------------------------------------------------------------------------

CSV_REPORT_ENGINE = ProjectSpec(
    slug="csv-report-engine",
    title="CSV Report Engine — The Monthly Numbers",
    tagline="The report finance asks for every month, built once, correctly, with the "
    "rounding done properly.",
    level=SkillLevel.INTERMEDIATE,
    guidance=GuidanceLevel.PARTIALLY_GUIDED,
    estimated_hours=4,
    xp_reward=250,
    concepts=("csv-data", "dictionaries", "sorting", "exceptions", "file-io"),
    prerequisites=("expense-tracker-cli",),
    requirements="""\
## The situation

Every month someone exports a CSV of transactions and rebuilds the same summary
by hand in a spreadsheet. It takes half a day and the totals are occasionally
wrong. Automate it.

## Input

```csv
date,region,product,units,unit_price_pence,currency
2026-08-03,EMEA,widget,12,1050,GBP
2026-08-04,APAC,gizmo,3,24999,GBP
```

Real exports are not clean. You must handle, without crashing:

- a missing or extra column
- blank rows
- `units` or `unit_price_pence` that is not a number
- a currency that is not GBP — these rows are **skipped and counted**, not converted
- duplicate rows, which are legitimate data and must not be deduplicated

## What it must do

1. Read the CSV and produce a per-region summary: total revenue, units sold,
   number of transactions, and the best-selling product by units.
2. Revenue is `units * unit_price_pence`, kept in **integer pence** throughout.
   Convert to pounds only when formatting.
3. Report rejected rows separately: how many, and why, grouped by reason.
4. Order regions by revenue descending.
5. Write the summary as CSV, and print a human-readable version.

## Constraints

- Standard library only — `csv`, not pandas.
- **No floats for money anywhere.** A test checks this.
- A bad row must not lose the good rows around it.
""",
    architecture_notes="""\
Integer pence is the whole point of the money handling. `0.1 + 0.2 != 0.3` in
binary floating point, and a monthly total built from floats drifts by pennies
that finance will notice. Parse to int, aggregate as int, divide by 100 exactly
once, at the moment you format.

Separate the three responsibilities: reading and validating rows, aggregating
valid rows, formatting output. That split is what lets you test the aggregation
without a file.

Use `csv.DictReader` — it handles quoting and gives you named access, which
matters when someone reorders the columns.

Rejections are output, not errors. A row that fails validation should produce a
structured reason you can group, not a print statement.
""",
    suggested_structure="""\
csv_report/
├── main.py
├── reading.py        # DictReader -> (valid rows, rejections)
├── aggregate.py      # rows -> per-region summary
├── formatting.py     # pence -> "£1,234.56", CSV writer
└── tests/
    ├── test_reading.py
    ├── test_aggregate.py
    └── test_formatting.py
""",
    milestones=(
        {
            "key": "read",
            "title": "Read and validate",
            "detail": "`read_rows(lines)` returns valid rows and a list of rejections with "
            "reasons. Get the reasons structured now, not as strings you parse later.",
        },
        {
            "key": "money",
            "title": "Integer pence",
            "detail": "Parse units and price to int. No float touches a monetary value.",
        },
        {
            "key": "aggregate",
            "title": "Per-region summary",
            "detail": "Revenue, units, transaction count, best-selling product by units.",
        },
        {
            "key": "format",
            "title": "Format",
            "detail": "Pence to pounds at the boundary only. Regions by revenue descending.",
        },
        {
            "key": "cli",
            "title": "Wire it up",
            "detail": "Read a path, write a CSV, print the summary, report rejections.",
        },
    ),
    starter_files={
        "reading.py": '''\
"""Read and validate transaction rows."""


def read_rows(lines) -> tuple[list[dict], list[dict]]:
    """Return (valid_rows, rejections).

    A valid row has int `units`, int `unit_price_pence`, a region, a product and
    currency GBP. A rejection is {"row": <original>, "reason": <short slug>}.
    """
    # Your code here
    ...
''',
        "aggregate.py": '''\
"""Aggregate valid rows into a per-region summary."""


def summarise(rows: list[dict]) -> list[dict]:
    """Per-region totals, ordered by revenue descending.

    Each entry: region, revenue_pence, units, transactions, best_product.
    """
    # Your code here
    ...
''',
        "formatting.py": '''\
"""Format money and write output."""


def format_pence(pence: int) -> str:
    """1234567 -> "£12,345.67"."""
    # Your code here
    ...
''',
        "README.md": "# CSV Report Engine\n\nInput columns, output columns, and the "
        "rejection reasons.\n",
    },
    acceptance_tests={
        "test_acceptance_csv.py": '''\
"""Acceptance tests: the contract, not your internal design."""

import pytest

HEADER = "date,region,product,units,unit_price_pence,currency"
GOOD = [
    HEADER,
    "2026-08-03,EMEA,widget,12,1050,GBP",
    "2026-08-04,EMEA,gizmo,3,2000,GBP",
    "2026-08-05,APAC,widget,5,1050,GBP",
]


def test_reads_valid_rows():
    reading = pytest.importorskip("reading", reason="create reading.py with read_rows()")
    rows, rejected = reading.read_rows(GOOD)
    assert len(rows) == 3
    assert rejected == []


def test_units_and_price_are_integers():
    reading = pytest.importorskip("reading")
    rows, _ = reading.read_rows(GOOD)
    assert isinstance(rows[0]["units"], int)
    assert isinstance(rows[0]["unit_price_pence"], int)
    assert not isinstance(rows[0]["unit_price_pence"], float), "money must never be a float"


def test_rejects_non_numeric_units_with_a_reason():
    reading = pytest.importorskip("reading")
    rows, rejected = reading.read_rows([HEADER, "2026-08-03,EMEA,widget,many,1050,GBP"])
    assert rows == []
    assert len(rejected) == 1
    assert rejected[0].get("reason"), "a rejection must carry a reason"


def test_rejects_foreign_currency_but_keeps_good_rows():
    reading = pytest.importorskip("reading")
    lines = GOOD + ["2026-08-06,EMEA,widget,1,1050,USD"]
    rows, rejected = reading.read_rows(lines)
    assert len(rows) == 3, "a rejected row must not lose the valid rows"
    assert len(rejected) == 1


def test_blank_rows_are_rejected_not_fatal():
    reading = pytest.importorskip("reading")
    rows, rejected = reading.read_rows([HEADER, "", "2026-08-03,EMEA,widget,1,100,GBP"])
    assert len(rows) == 1


def test_duplicates_are_kept():
    reading = pytest.importorskip("reading")
    dup = "2026-08-03,EMEA,widget,12,1050,GBP"
    rows, _ = reading.read_rows([HEADER, dup, dup])
    assert len(rows) == 2, "duplicate transactions are real data, not noise"


def test_summarise_totals_revenue_in_pence():
    reading = pytest.importorskip("reading")
    aggregate = pytest.importorskip("aggregate", reason="create aggregate.py")
    rows, _ = reading.read_rows(GOOD)
    summary = {s["region"]: s for s in aggregate.summarise(rows)}
    assert summary["EMEA"]["revenue_pence"] == 12 * 1050 + 3 * 2000
    assert summary["APAC"]["revenue_pence"] == 5 * 1050


def test_summarise_orders_by_revenue_descending():
    reading = pytest.importorskip("reading")
    aggregate = pytest.importorskip("aggregate")
    rows, _ = reading.read_rows(GOOD)
    regions = [s["region"] for s in aggregate.summarise(rows)]
    assert regions == ["EMEA", "APAC"]


def test_summarise_reports_units_and_transactions():
    reading = pytest.importorskip("reading")
    aggregate = pytest.importorskip("aggregate")
    rows, _ = reading.read_rows(GOOD)
    emea = next(s for s in aggregate.summarise(rows) if s["region"] == "EMEA")
    assert emea["units"] == 15
    assert emea["transactions"] == 2


def test_summarise_finds_best_selling_product_by_units():
    reading = pytest.importorskip("reading")
    aggregate = pytest.importorskip("aggregate")
    rows, _ = reading.read_rows(GOOD)
    emea = next(s for s in aggregate.summarise(rows) if s["region"] == "EMEA")
    assert emea["best_product"] == "widget", "12 units beats 3"


def test_empty_input():
    reading = pytest.importorskip("reading")
    aggregate = pytest.importorskip("aggregate")
    rows, _ = reading.read_rows([HEADER])
    assert aggregate.summarise(rows) == []


def test_format_pence_uses_thousands_separators():
    formatting = pytest.importorskip("formatting", reason="create formatting.py")
    assert formatting.format_pence(1234567) == "\\u00a312,345.67"


def test_format_pence_pads_the_pennies():
    formatting = pytest.importorskip("formatting")
    assert formatting.format_pence(105) == "\\u00a31.05"
    assert formatting.format_pence(100) == "\\u00a31.00"
''',
    },
    rubric=STANDARD_RUBRIC,
)

# ---------------------------------------------------------------------------
# 3 — Resilient API client
# ---------------------------------------------------------------------------

API_CLIENT_SDK = ProjectSpec(
    slug="api-client-sdk",
    title="API Client — Retries, Backoff and Pagination",
    tagline="The wrapper every team writes around a flaky third-party API, done properly "
    "and testable without a network.",
    level=SkillLevel.INTERMEDIATE,
    guidance=GuidanceLevel.PARTIALLY_GUIDED,
    estimated_hours=4,
    xp_reward=280,
    concepts=("api-clients", "http-basics", "exceptions", "custom-exceptions", "test-design"),
    prerequisites=("expense-tracker-cli",),
    requirements="""\
## The situation

You depend on a partner API that is *mostly* fine. It rate-limits under load,
occasionally returns a 502, paginates everything, and its timeouts are
unpredictable. Right now every caller in your codebase handles that differently,
or not at all.

Build the client that handles it once.

## The transport seam

Your client must not import a HTTP library. It takes a `send` callable:

```python
client = ApiClient(send=send, base_url="https://api.example.com", token="secret")
```

`send(method, url, headers, body)` returns a `Response` with `.status`,
`.headers` and `.json()`. In production you pass an adapter around `requests`; in
tests the suite passes a fake. This is the design the project is really teaching:
the retry logic is the valuable part, and it is only testable if the transport is
injectable.

## What it must do

1. **Classify** responses: 2xx success; 4xx a permanent client error that must
   **not** be retried (except 429); 5xx and 429 transient.
2. **Retry** transient failures up to `max_retries` with exponential backoff,
   `base_delay * 2 ** attempt`. Honour a `Retry-After` header when present, in
   preference to your own backoff.
3. **Sleep** through an injected `sleep` callable, so tests do not actually wait.
4. **Raise** typed errors: `AuthError` on 401/403, `NotFoundError` on 404,
   `RateLimitError` when retries are exhausted on 429, `ApiError` otherwise.
   Each must carry the status and the response body.
5. **Paginate**: `iter_all(path)` yields every item across pages, following the
   `next` cursor in the response until it is absent. It must be a generator —
   ten thousand items must not become a ten-thousand-item list.
6. **Never log the token.** A test greps your log output for it.

## Constraints

- Standard library only. No `requests` import anywhere in your code.
- Backoff must be deterministic given the injected sleep, so it can be asserted.
""",
    architecture_notes="""\
Dependency injection is the architectural point. A client that constructs its own
HTTP session can only be tested against a real server or a monkeypatched module;
one that accepts `send` and `sleep` is testable with two tiny fakes and no
waiting. Notice that this also makes the retry policy assertable — you can check
*how long* it would have slept.

Classify before you retry. The commonest bug in hand-rolled clients is retrying a
400: the request is malformed, so trying it four more times just wastes four more
round trips and delays the real error.

`Retry-After` exists because the server knows better than your backoff formula.
Prefer it when present.

Make `iter_all` a generator. The moment it returns a list, the memory profile
becomes the size of the dataset and callers lose the ability to stop early.
""",
    suggested_structure="""\
api_client/
├── client.py         # ApiClient: request(), iter_all()
├── errors.py         # ApiError and its subclasses
├── retry.py          # classification + backoff calculation
└── tests/
    ├── fakes.py      # FakeTransport, recording sleep
    ├── test_retry.py
    └── test_client.py
""",
    milestones=(
        {
            "key": "errors",
            "title": "The error hierarchy",
            "detail": "A base ApiError carrying status and body, with AuthError, "
            "NotFoundError and RateLimitError beneath it.",
        },
        {
            "key": "classify",
            "title": "Classify a response",
            "detail": "Success, permanent or transient. 429 is transient even though it is "
            "a 4xx — that distinction is the whole function.",
        },
        {
            "key": "backoff",
            "title": "Backoff",
            "detail": "base_delay * 2 ** attempt, overridden by Retry-After. Sleep through "
            "the injected callable.",
        },
        {
            "key": "request",
            "title": "request() with retries",
            "detail": "Retry transient failures, raise typed errors, stop immediately on a "
            "permanent one.",
        },
        {
            "key": "paginate",
            "title": "iter_all()",
            "detail": "Follow the next cursor, yielding items lazily.",
        },
    ),
    starter_files={
        "errors.py": '''\
"""Typed errors, so callers can react to the kind of failure."""


class ApiError(Exception):
    """Base: any failed API interaction. Carries status and body."""

    def __init__(self, message: str, status: int | None = None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


# Your code here: AuthError, NotFoundError, RateLimitError
''',
        "retry.py": '''\
"""Decide whether to retry, and how long to wait."""

SUCCESS = "success"
PERMANENT = "permanent"
TRANSIENT = "transient"


def classify(status: int) -> str:
    """One of SUCCESS, PERMANENT, TRANSIENT."""
    # Your code here
    ...


def backoff_seconds(attempt: int, base_delay: float, retry_after: str | None = None) -> float:
    """Seconds to wait before the next attempt. Retry-After wins when present."""
    # Your code here
    ...
''',
        "client.py": '''\
"""The client. Note what it does NOT import."""


class ApiClient:
    def __init__(self, send, base_url: str, token: str, *, sleep=None,
                 max_retries: int = 3, base_delay: float = 0.5):
        # Your code here
        ...

    def request(self, method: str, path: str, body=None):
        """Perform a request with retries. Return the decoded JSON."""
        # Your code here
        ...

    def iter_all(self, path: str):
        """Yield every item across all pages. Must be a generator."""
        # Your code here
        ...
''',
        "README.md": "# API Client\n\nHow to inject a real transport, and what each error "
        "means to a caller.\n",
    },
    acceptance_tests={
        "test_acceptance_client.py": '''\
"""Acceptance tests: the contract, not your internal design.

No network anywhere: the transport is a fake, and sleeping is recorded rather
than performed. That is the design this project is teaching.
"""

import inspect

import pytest


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status = status
        self.headers = headers or {}
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


class FakeTransport:
    """Returns queued responses in order; records every call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers=None, body=None):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "body": body})
        if not self.responses:
            raise AssertionError("transport called more times than the test queued responses")
        return self.responses.pop(0)


class RecordingSleep:
    def __init__(self):
        self.waits = []

    def __call__(self, seconds):
        self.waits.append(seconds)


def _client(responses, **kwargs):
    client_mod = pytest.importorskip("client", reason="create client.py with ApiClient")
    transport = FakeTransport(responses)
    sleeper = RecordingSleep()
    client = client_mod.ApiClient(
        send=transport, base_url="https://api.example.com", token="secret-token",
        sleep=sleeper, **kwargs
    )
    return client, transport, sleeper


def test_classify_success_permanent_transient():
    retry = pytest.importorskip("retry", reason="create retry.py with classify()")
    assert retry.classify(200) == retry.SUCCESS
    assert retry.classify(400) == retry.PERMANENT
    assert retry.classify(404) == retry.PERMANENT
    assert retry.classify(500) == retry.TRANSIENT
    assert retry.classify(503) == retry.TRANSIENT


def test_classify_treats_429_as_transient():
    retry = pytest.importorskip("retry")
    assert retry.classify(429) == retry.TRANSIENT, (
        "429 is a 4xx but it is worth retrying — that is the point of the function"
    )


def test_backoff_is_exponential():
    retry = pytest.importorskip("retry")
    assert retry.backoff_seconds(0, 0.5) == pytest.approx(0.5)
    assert retry.backoff_seconds(1, 0.5) == pytest.approx(1.0)
    assert retry.backoff_seconds(2, 0.5) == pytest.approx(2.0)


def test_retry_after_overrides_backoff():
    retry = pytest.importorskip("retry")
    assert retry.backoff_seconds(0, 0.5, retry_after="7") == pytest.approx(7.0)


def test_successful_request_returns_decoded_json():
    client, transport, _ = _client([FakeResponse(200, {"ok": True})])
    assert client.request("GET", "/things") == {"ok": True}
    assert len(transport.calls) == 1


def test_sends_the_bearer_token():
    client, transport, _ = _client([FakeResponse(200, {})])
    client.request("GET", "/things")
    headers = transport.calls[0]["headers"]
    joined = " ".join(f"{k}: {v}" for k, v in headers.items())
    assert "secret-token" in joined, "the token must be sent in the request headers"


def test_retries_a_500_then_succeeds():
    client, transport, sleeper = _client(
        [FakeResponse(500), FakeResponse(500), FakeResponse(200, {"ok": 1})]
    )
    assert client.request("GET", "/things") == {"ok": 1}
    assert len(transport.calls) == 3
    assert len(sleeper.waits) == 2, "one sleep between each pair of attempts"


def test_does_not_retry_a_400():
    errors = pytest.importorskip("errors", reason="create errors.py")
    client, transport, _ = _client([FakeResponse(400, {"error": "bad"})])
    with pytest.raises(errors.ApiError):
        client.request("GET", "/things")
    assert len(transport.calls) == 1, "a 400 is permanent — retrying wastes round trips"


def test_401_raises_auth_error():
    errors = pytest.importorskip("errors")
    client, _, _ = _client([FakeResponse(401)])
    with pytest.raises(errors.AuthError):
        client.request("GET", "/things")


def test_404_raises_not_found():
    errors = pytest.importorskip("errors")
    client, _, _ = _client([FakeResponse(404)])
    with pytest.raises(errors.NotFoundError):
        client.request("GET", "/things")


def test_exhausted_429_raises_rate_limit_error():
    errors = pytest.importorskip("errors")
    client, _, _ = _client([FakeResponse(429) for _ in range(4)], max_retries=3)
    with pytest.raises(errors.RateLimitError):
        client.request("GET", "/things")


def test_error_carries_status_and_body():
    errors = pytest.importorskip("errors")
    client, _, _ = _client([FakeResponse(400, {"detail": "nope"})])
    with pytest.raises(errors.ApiError) as caught:
        client.request("GET", "/things")
    assert caught.value.status == 400
    assert caught.value.body == {"detail": "nope"}


def test_honours_retry_after_header():
    client, _, sleeper = _client(
        [FakeResponse(429, headers={"Retry-After": "3"}), FakeResponse(200, {})]
    )
    client.request("GET", "/things")
    assert sleeper.waits == [pytest.approx(3.0)], "the server's Retry-After wins over backoff"


def test_iter_all_follows_pagination():
    client, _, _ = _client([
        FakeResponse(200, {"items": [1, 2], "next": "cursor-1"}),
        FakeResponse(200, {"items": [3], "next": None}),
    ])
    assert list(client.iter_all("/things")) == [1, 2, 3]


def test_iter_all_is_lazy():
    client_mod = pytest.importorskip("client")
    assert inspect.isgeneratorfunction(client_mod.ApiClient.iter_all), (
        "iter_all must be a generator so a large dataset is never materialised"
    )


def test_client_does_not_import_a_http_library():
    client_mod = pytest.importorskip("client")
    source = inspect.getsource(client_mod)
    for banned in ("import requests", "import urllib", "import http.client", "import httpx"):
        assert banned not in source, (
            f"{banned!r} defeats the transport seam — the client takes a send callable"
        )
''',
    },
    rubric=STANDARD_RUBRIC,
)

# ---------------------------------------------------------------------------
# 4 — Invoice reconciliation
# ---------------------------------------------------------------------------

INVOICE_RECONCILIATION = ProjectSpec(
    slug="invoice-reconciliation",
    title="Invoice Reconciliation — Match the Money",
    tagline="Two systems disagree about what was paid. Find every discrepancy and classify it.",
    level=SkillLevel.PROFESSIONAL,
    guidance=GuidanceLevel.REQUIREMENTS_ONLY,
    estimated_hours=5,
    xp_reward=350,
    concepts=("dictionaries", "sets", "csv-data", "custom-exceptions", "complexity"),
    prerequisites=("csv-report-engine",),
    requirements="""\
## Business requirement

Finance runs two exports: invoices raised by our billing system, and payments
recorded by the bank. Every month someone compares them in a spreadsheet and
finds a handful of problems. It takes two days and mistakes reach customers.

Build the reconciliation. **You choose the design** — this brief states the
contract and nothing else.

## Inputs

`invoices.csv`: `invoice_id,customer_id,amount_pence,issued_date,due_date`
`payments.csv`: `payment_ref,invoice_id,amount_pence,paid_date`

## Required output

A reconciliation report classifying every invoice and payment into exactly one
category:

| Category | Meaning |
| --- | --- |
| `matched` | one payment, amount equal to the invoice |
| `underpaid` | payments total less than the invoice |
| `overpaid` | payments total more than the invoice |
| `unpaid` | no payment at all, and past its due date |
| `outstanding` | no payment, not yet due |
| `orphan_payment` | payment referencing an invoice that does not exist |
| `duplicate_payment` | two payments with the same `payment_ref` |

An invoice may have **several** payments — instalments are normal, and their sum
is what matters.

## Contract

Expose a module-level function:

```python
reconcile(invoices, payments, as_of) -> dict
```

`invoices` and `payments` are lists of dicts with the columns above and integer
`amount_pence`. `as_of` is an ISO date string deciding `unpaid` versus
`outstanding`. Return a dict whose keys are the category names above, each mapping
to a list of records. Include a `"totals"` key: per category, the count and the
summed pence.

## Constraints

- Integer pence throughout. No floats.
- Must be linear in the number of invoices plus payments. A nested scan over
  payments for each invoice will fail a scale test.
- A duplicate `payment_ref` is reported *and* excluded from the amount matching,
  so a duplicate cannot turn a matched invoice into an overpayment.
""",
    architecture_notes="""\
This is a grouping problem wearing a finance costume. Index the payments by
`invoice_id` once, then every invoice is a dict lookup — that is the difference
between linear and quadratic, and the scale test enforces it.

The ordering of the rules matters and is worth writing down before you code:
duplicates are detected first (on `payment_ref`), then orphans (no matching
invoice), and only then are the surviving payments summed per invoice to decide
matched/under/over/unpaid/outstanding. Getting this order wrong is how a
duplicate becomes an overpayment.

`as_of` being a parameter rather than `date.today()` is deliberate. A function
that reads the clock cannot be tested, and reconciliation is exactly the kind of
job that gets re-run over a historical period.
""",
    milestones=(
        {
            "key": "contract",
            "title": "Write the contract test first",
            "detail": "You have the required shape. Write a test for a matched invoice "
            "before writing reconcile().",
        },
        {
            "key": "index",
            "title": "Index payments by invoice",
            "detail": "Once, up front. Everything after this is a lookup.",
        },
        {
            "key": "rules",
            "title": "Apply the rules in order",
            "detail": "Duplicates, then orphans, then sums. Write the order down.",
        },
        {
            "key": "totals",
            "title": "Totals",
            "detail": "Count and summed pence per category.",
        },
        {
            "key": "scale",
            "title": "Check it scales",
            "detail": "50k invoices and 50k payments should reconcile in well under a second.",
        },
    ),
    starter_files={
        "README.md": """\
# Invoice Reconciliation

You design this one. The only fixed points are:

- a module-level `reconcile(invoices, payments, as_of)` importable from somewhere
  the acceptance tests can reach — put it in `reconciliation.py`
- the return shape described in the requirements

Write your own tests as well as passing the acceptance tests. The acceptance
tests check the contract; they are not a substitute for a suite of your own.
"""
    },
    acceptance_tests={
        "test_acceptance_reconcile.py": '''\
"""Acceptance tests: the contract only. The design is yours."""

import time

import pytest


def _reconcile():
    module = pytest.importorskip(
        "reconciliation",
        reason="create reconciliation.py exposing reconcile(invoices, payments, as_of)",
    )
    assert hasattr(module, "reconcile"), "reconciliation.py must expose reconcile()"
    return module.reconcile


def inv(invoice_id, amount, customer="c1", issued="2026-08-01", due="2026-08-31"):
    return {
        "invoice_id": invoice_id, "customer_id": customer, "amount_pence": amount,
        "issued_date": issued, "due_date": due,
    }


def pay(ref, invoice_id, amount, paid="2026-08-15"):
    return {
        "payment_ref": ref, "invoice_id": invoice_id,
        "amount_pence": amount, "paid_date": paid,
    }


AS_OF = "2026-09-15"


def test_exact_payment_is_matched():
    result = _reconcile()([inv("INV1", 1000)], [pay("P1", "INV1", 1000)], AS_OF)
    assert len(result["matched"]) == 1
    assert result["underpaid"] == [] and result["overpaid"] == []


def test_instalments_summing_to_the_invoice_are_matched():
    result = _reconcile()(
        [inv("INV1", 1000)], [pay("P1", "INV1", 400), pay("P2", "INV1", 600)], AS_OF
    )
    assert len(result["matched"]) == 1, "several payments summing to the total is a match"


def test_short_payment_is_underpaid():
    result = _reconcile()([inv("INV1", 1000)], [pay("P1", "INV1", 900)], AS_OF)
    assert len(result["underpaid"]) == 1


def test_excess_payment_is_overpaid():
    result = _reconcile()([inv("INV1", 1000)], [pay("P1", "INV1", 1100)], AS_OF)
    assert len(result["overpaid"]) == 1


def test_no_payment_past_due_is_unpaid():
    result = _reconcile()([inv("INV1", 1000, due="2026-08-31")], [], AS_OF)
    assert len(result["unpaid"]) == 1
    assert result["outstanding"] == []


def test_no_payment_not_yet_due_is_outstanding():
    result = _reconcile()([inv("INV1", 1000, due="2026-12-31")], [], AS_OF)
    assert len(result["outstanding"]) == 1
    assert result["unpaid"] == []


def test_payment_for_unknown_invoice_is_an_orphan():
    result = _reconcile()([], [pay("P1", "NOPE", 500)], AS_OF)
    assert len(result["orphan_payment"]) == 1


def test_duplicate_payment_ref_is_reported():
    result = _reconcile()(
        [inv("INV1", 1000)], [pay("P1", "INV1", 1000), pay("P1", "INV1", 1000)], AS_OF
    )
    assert len(result["duplicate_payment"]) >= 1


def test_duplicate_does_not_create_an_overpayment():
    result = _reconcile()(
        [inv("INV1", 1000)], [pay("P1", "INV1", 1000), pay("P1", "INV1", 1000)], AS_OF
    )
    assert result["overpaid"] == [], (
        "the duplicate must be excluded from matching, or a matched invoice "
        "looks overpaid — detect duplicates before summing"
    )
    assert len(result["matched"]) == 1


def test_every_category_key_is_present_even_when_empty():
    result = _reconcile()([], [], AS_OF)
    for key in ("matched", "underpaid", "overpaid", "unpaid", "outstanding",
                "orphan_payment", "duplicate_payment", "totals"):
        assert key in result, f"the report must always include {key!r}"


def test_totals_carry_count_and_summed_pence():
    result = _reconcile()(
        [inv("INV1", 1000), inv("INV2", 2000)],
        [pay("P1", "INV1", 1000), pay("P2", "INV2", 2000)],
        AS_OF,
    )
    matched = result["totals"]["matched"]
    assert matched["count"] == 2
    assert matched["amount_pence"] == 3000


def test_amounts_are_never_floats():
    result = _reconcile()([inv("INV1", 1000)], [pay("P1", "INV1", 999)], AS_OF)
    total = result["totals"]["underpaid"]["amount_pence"]
    assert isinstance(total, int) and not isinstance(total, bool), "money stays integer pence"


def test_reconciles_linearly():
    reconcile = _reconcile()
    invoices = [inv(f"INV{i}", 1000) for i in range(50_000)]
    payments = [pay(f"P{i}", f"INV{i}", 1000) for i in range(50_000)]
    start = time.perf_counter()
    result = reconcile(invoices, payments, AS_OF)
    elapsed = time.perf_counter() - start
    assert len(result["matched"]) == 50_000
    assert elapsed < 5.0, (
        f"took {elapsed:.1f}s — index the payments by invoice_id once instead of "
        "scanning all payments for every invoice"
    )
''',
    },
    rubric=STANDARD_RUBRIC,
)

# ---------------------------------------------------------------------------
# 5 — ETL pipeline
# ---------------------------------------------------------------------------

ETL_PIPELINE = ProjectSpec(
    slug="etl-pipeline",
    title="ETL Pipeline — Load It Without Losing It",
    tagline="Extract, validate, transform, load — and be able to prove afterwards exactly "
    "what happened to every record.",
    level=SkillLevel.PROFESSIONAL,
    guidance=GuidanceLevel.REQUIREMENTS_ONLY,
    estimated_hours=5,
    xp_reward=350,
    concepts=("file-io", "json-data", "csv-data", "generators", "logging", "custom-exceptions"),
    prerequisites=("csv-report-engine",),
    requirements="""\
## Business requirement

A partner drops a daily JSON-lines file of product records into a directory. It
needs validating, normalising and loading into our catalogue. The current script
loads what it can, prints a few warnings, and nobody can answer "did record
84,102 make it in, and if not, why?"

Build the pipeline that can answer that. **You choose the design.**

## Input

One JSON object per line:

```json
{"sku": " ab-123 ", "name": "Widget", "price": "10.50", "currency": "GBP", "stock": "7"}
```

Real files contain: leading and trailing whitespace, `sku` in mixed case,
`price` as a string with a decimal point, missing optional fields, absent
required fields, duplicate SKUs, and lines that are not valid JSON at all.

## Required behaviour

1. **Extract** lazily, one line at a time. The file may be larger than memory.
2. **Validate**: `sku`, `name` and `price` are required. `stock` defaults to 0.
   `currency` defaults to `GBP` and must be one of GBP, EUR, USD.
3. **Transform**: strip whitespace, upper-case the `sku`, convert `price` to
   **integer pence**, coerce `stock` to int.
4. **Deduplicate** on `sku` — the **last** record in the file wins, and the
   supersession is recorded.
5. **Load** through an injected `load(records)` callable, in batches of
   `batch_size`. A batch that raises must not abort the run: record the failure,
   continue with the next batch.
6. **Report** a run summary: read, valid, rejected by reason, superseded, loaded,
   failed to load. The counts must reconcile — every record read is accounted for
   in exactly one outcome.

## Contract

```python
run(lines, load, batch_size=100) -> RunReport
```

`RunReport` may be a dataclass or a dict, but must expose the counts above and a
`rejections` collection of `(line_number, reason)`.

## Constraints

- Standard library only.
- No float touches `price`.
- Extraction must be a generator. A test inspects for this.
- Line numbers in rejections are 1-based, so they match what an editor shows.
""",
    architecture_notes="""\
Reconciling counts is the requirement that shapes everything: read must equal
loaded + rejected + superseded + failed. That forces each record down exactly one
path, which in turn forces you to decide what happens to a record that is both a
duplicate *and* invalid. Decide, write it down, and test it.

Generators compose here in a way that is worth feeling: extract yields raw lines,
validate yields either a record or a rejection, transform maps records — and
nothing is materialised until the batcher groups them. Memory stays flat
regardless of file size.

Deduplication with last-wins fights laziness, because you cannot know a record is
superseded until you have seen the whole file. Two honest options: buffer only the
SKU-to-record map (bounded by distinct SKUs, not by file size), or do two passes.
Either is defensible; say which you chose and why.

The injected `load` is the same seam as the API client project. It makes a
batch-failure test possible without a database.
""",
    milestones=(
        {
            "key": "extract",
            "title": "Lazy extract",
            "detail": "A generator over lines yielding parsed JSON or a rejection. "
            "1-based line numbers.",
        },
        {
            "key": "validate",
            "title": "Validate and transform",
            "detail": "Required fields, defaults, allowed currencies, price to pence.",
        },
        {
            "key": "dedupe",
            "title": "Last-wins deduplication",
            "detail": "Record supersessions rather than silently dropping them.",
        },
        {
            "key": "load",
            "title": "Batched load with failure isolation",
            "detail": "A raising batch is recorded; the run continues.",
        },
        {
            "key": "reconcile",
            "title": "Make the counts reconcile",
            "detail": "read == loaded + rejected + superseded + failed. Assert it in your "
            "own test suite.",
        },
    ),
    starter_files={
        "README.md": """\
# ETL Pipeline

You design this one. Fixed points:

- `run(lines, load, batch_size=100)` importable from `pipeline.py`
- a report exposing the counts in the requirements, plus `rejections`
- extraction is a generator

State your deduplication strategy in this README and why you chose it.
"""
    },
    acceptance_tests={
        "test_acceptance_etl.py": '''\
"""Acceptance tests: the contract only. The design is yours."""

import inspect
import json

import pytest


def _run():
    module = pytest.importorskip(
        "pipeline", reason="create pipeline.py exposing run(lines, load, batch_size=100)"
    )
    assert hasattr(module, "run"), "pipeline.py must expose run()"
    return module.run


def line(**fields):
    return json.dumps(fields)


def _count(report, name):
    """Counts may be attributes or dict keys."""
    if isinstance(report, dict):
        return report[name]
    return getattr(report, name)


class Loader:
    def __init__(self, fail_on_batch=None):
        self.batches = []
        self.fail_on_batch = fail_on_batch

    def __call__(self, records):
        self.batches.append(list(records))
        if self.fail_on_batch is not None and len(self.batches) == self.fail_on_batch:
            raise RuntimeError("simulated database failure")


GOOD = line(sku="ab-1", name="Widget", price="10.50", currency="GBP", stock="7")


def test_loads_a_valid_record():
    loader = Loader()
    report = _run()([GOOD], loader)
    assert _count(report, "loaded") == 1
    assert loader.batches[0][0]["sku"] == "AB-1", "sku is upper-cased and stripped"


def test_price_becomes_integer_pence():
    loader = Loader()
    _run()([GOOD], loader)
    record = loader.batches[0][0]
    assert record["price_pence"] == 1050, "10.50 -> 1050 pence"
    assert isinstance(record["price_pence"], int)


def test_stock_defaults_to_zero():
    loader = Loader()
    _run()([line(sku="a", name="n", price="1.00")], loader)
    assert loader.batches[0][0]["stock"] == 0


def test_currency_defaults_to_gbp():
    loader = Loader()
    _run()([line(sku="a", name="n", price="1.00")], loader)
    assert loader.batches[0][0]["currency"] == "GBP"


def test_missing_required_field_is_rejected():
    loader = Loader()
    report = _run()([line(sku="a", price="1.00")], loader)
    assert _count(report, "loaded") == 0
    rejections = _count(report, "rejections")
    assert len(rejections) == 1


def test_invalid_json_is_rejected_with_a_line_number():
    loader = Loader()
    report = _run()(["{not json", GOOD], loader)
    rejections = list(_count(report, "rejections"))
    assert _count(report, "loaded") == 1, "one bad line must not lose the good one"
    assert rejections[0][0] == 1, "line numbers are 1-based so they match an editor"


def test_disallowed_currency_is_rejected():
    loader = Loader()
    report = _run()([line(sku="a", name="n", price="1.00", currency="JPY")], loader)
    assert _count(report, "loaded") == 0


def test_duplicate_sku_last_one_wins():
    loader = Loader()
    lines = [
        line(sku="a", name="first", price="1.00"),
        line(sku="a", name="second", price="2.00"),
    ]
    report = _run()(lines, loader)
    loaded = [r for batch in loader.batches for r in batch]
    assert len(loaded) == 1
    assert loaded[0]["name"] == "second", "the later record supersedes the earlier one"
    assert _count(report, "superseded") == 1


def test_batches_respect_batch_size():
    loader = Loader()
    lines = [line(sku=f"s{i}", name="n", price="1.00") for i in range(25)]
    _run()(lines, loader, batch_size=10)
    assert [len(b) for b in loader.batches] == [10, 10, 5]


def test_a_failing_batch_does_not_abort_the_run():
    loader = Loader(fail_on_batch=1)
    lines = [line(sku=f"s{i}", name="n", price="1.00") for i in range(20)]
    report = _run()(lines, loader, batch_size=10)
    assert len(loader.batches) == 2, "the second batch must still be attempted"
    assert _count(report, "failed") == 10
    assert _count(report, "loaded") == 10


def test_counts_reconcile():
    loader = Loader()
    lines = [
        GOOD,
        "{not json",
        line(sku="x", price="1.00"),
        line(sku="ab-1", name="dup", price="3.00"),
    ]
    report = _run()(lines, loader)
    read = _count(report, "read")
    accounted = (
        _count(report, "loaded")
        + len(list(_count(report, "rejections")))
        + _count(report, "superseded")
        + _count(report, "failed")
    )
    assert read == accounted, (
        f"read={read} but only {accounted} records are accounted for — "
        "every record must end in exactly one outcome"
    )


def test_empty_input():
    loader = Loader()
    report = _run()([], loader)
    assert _count(report, "read") == 0
    assert _count(report, "loaded") == 0


def test_extraction_is_lazy():
    module = pytest.importorskip("pipeline")
    generators = [
        name for name, fn in vars(module).items()
        if inspect.isgeneratorfunction(fn)
    ]
    assert generators, (
        "no generator function found in pipeline.py — extraction must stream, "
        "so the file can be larger than memory"
    )
''',
    },
    rubric=STANDARD_RUBRIC,
)

# ---------------------------------------------------------------------------
# 6 — Inventory sync
# ---------------------------------------------------------------------------

INVENTORY_SYNC = ProjectSpec(
    slug="inventory-sync-service",
    title="Inventory Sync — Two Systems, One Truth",
    tagline="The warehouse and the website disagree about stock. Decide who is right, "
    "safely, and be able to undo it.",
    level=SkillLevel.PROFESSIONAL,
    guidance=GuidanceLevel.REQUIREMENTS_ONLY,
    estimated_hours=6,
    xp_reward=420,
    concepts=(
        "dictionaries",
        "sets",
        "logging",
        "custom-exceptions",
        "automation-design",
        "security-basics",
    ),
    prerequisites=("invoice-reconciliation",),
    requirements="""\
## Business requirement

The warehouse system and the storefront both hold stock levels. They drift. When
the storefront thinks there are 5 and there is 1, we oversell; when it thinks 0
and there are 40, we lose sales.

Build the sync. It runs unattended every fifteen minutes, so the hard
requirements are about **safety**, not about matching numbers.

## Inputs

Two snapshots, each a list of dicts:

```python
warehouse = [{"sku": "AB-1", "quantity": 12, "updated_at": "2026-09-11T02:00:00Z"}]
storefront = [{"sku": "AB-1", "quantity": 5,  "updated_at": "2026-09-11T01:00:00Z"}]
```

## Required behaviour

1. **Resolve** each SKU to a target quantity. The warehouse is authoritative
   *unless* the storefront record is strictly newer, in which case the sync makes
   no change and flags the SKU for review.
2. **Plan before acting.** Produce a plan of intended changes; do not apply
   anything during planning. The plan must be inspectable and serialisable.
3. **Guard rails**, any of which makes the whole run refuse to apply:
   - more than `max_change_ratio` (default 0.30) of SKUs would change
   - any single change is larger than `max_delta` (default 500) units
   - a target quantity is negative
4. **Apply** through an injected `apply(changes)` callable, in one call.
5. **Handle divergent sets**: a SKU only in the warehouse is *new* and must be
   created; a SKU only in the storefront is *delisted* and reported, never
   silently zeroed.
6. **Produce an undo plan** — the changes that would restore the previous
   storefront state — as part of the result.
7. **Log** every decision at a level that lets an engineer reconstruct the run
   from logs alone. Never log a full snapshot.

## Contract

```python
plan_sync(warehouse, storefront, **limits) -> SyncPlan
apply_sync(plan, apply) -> SyncResult
```

Two functions, so the plan can be reviewed without applying it. `SyncPlan` must
expose `changes`, `creates`, `delisted`, `review`, `undo`, and `refused`
(a list of guard-rail violations, empty when safe).

## Constraints

- Standard library only.
- `apply_sync` must refuse to act on a plan whose `refused` is non-empty.
- Must be linear in the number of SKUs.
""",
    architecture_notes="""\
Plan-then-apply is the architecture, and it is the pattern behind `terraform
plan`, database migrations and every deployment tool worth using. It exists
because the interesting failure is not "the sync was wrong" but "the sync was
wrong and had already run everywhere". Separating the decision from the action
makes the decision reviewable, testable and loggable, and makes a dry run free.

Guard rails are about blast radius, not correctness. A sync that changes 3% of
SKUs is routine; one that changes 90% means an input was truncated or a field was
renamed upstream — the *code* is fine and the *run* must not proceed. Refusing
loudly is the correct behaviour, which is why refusal is a first-class part of the
plan rather than an exception.

The undo plan is what makes this safe to run unattended. Build it from the
observed previous state at planning time; do not try to reconstruct it afterwards.

Comparing timestamps as ISO 8601 strings works because that format sorts
lexicographically when the timezone is uniform. Say so in a comment, because the
next reader will assume it is a bug.
""",
    milestones=(
        {
            "key": "index",
            "title": "Index both sides",
            "detail": "Dicts by SKU, and the three set relationships: both, warehouse-only, "
            "storefront-only.",
        },
        {
            "key": "resolve",
            "title": "Resolve targets",
            "detail": "Warehouse wins unless the storefront is strictly newer.",
        },
        {
            "key": "guard",
            "title": "Guard rails",
            "detail": "Ratio, per-change delta, negative targets. Refusals go in the plan.",
        },
        {
            "key": "undo",
            "title": "Undo plan",
            "detail": "Built at planning time from the previous storefront state.",
        },
        {
            "key": "apply",
            "title": "Apply, and refuse",
            "detail": "One injected call. Refuse outright when the plan is unsafe.",
        },
    ),
    starter_files={
        "README.md": """\
# Inventory Sync

You design this one. Fixed points:

- `plan_sync(warehouse, storefront, **limits)` and `apply_sync(plan, apply)`
  importable from `sync.py`
- a plan exposing changes, creates, delisted, review, undo, refused

Document your guard-rail defaults and what an operator should do when a run is
refused.
"""
    },
    acceptance_tests={
        "test_acceptance_sync.py": '''\
"""Acceptance tests: the contract only. The design is yours."""

import pytest


def _mod():
    return pytest.importorskip(
        "sync", reason="create sync.py exposing plan_sync() and apply_sync()"
    )


def wh(sku, qty, at="2026-09-11T02:00:00Z"):
    return {"sku": sku, "quantity": qty, "updated_at": at}


def sf(sku, qty, at="2026-09-11T01:00:00Z"):
    return {"sku": sku, "quantity": qty, "updated_at": at}


def _field(obj, name):
    return obj[name] if isinstance(obj, dict) else getattr(obj, name)


class Applier:
    def __init__(self):
        self.calls = []

    def __call__(self, changes):
        self.calls.append(list(changes))


def test_warehouse_wins_when_newer():
    plan = _mod().plan_sync([wh("A", 12)], [sf("A", 5)])
    changes = _field(plan, "changes")
    assert len(changes) == 1
    assert _field(changes[0], "sku") if not isinstance(changes[0], dict) else changes[0]["sku"] == "A"


def test_no_change_when_quantities_already_agree():
    plan = _mod().plan_sync([wh("A", 5)], [sf("A", 5)])
    assert _field(plan, "changes") == []


def test_newer_storefront_is_flagged_for_review_not_overwritten():
    plan = _mod().plan_sync(
        [wh("A", 12, at="2026-09-11T01:00:00Z")],
        [sf("A", 5, at="2026-09-11T02:00:00Z")],
    )
    assert _field(plan, "changes") == [], "a newer storefront record must not be overwritten"
    assert len(_field(plan, "review")) == 1


def test_warehouse_only_sku_is_a_create():
    plan = _mod().plan_sync([wh("NEW", 3)], [])
    assert len(_field(plan, "creates")) == 1
    assert _field(plan, "changes") == []


def test_storefront_only_sku_is_delisted_not_zeroed():
    plan = _mod().plan_sync([], [sf("OLD", 4)])
    assert len(_field(plan, "delisted")) == 1
    assert _field(plan, "changes") == [], "a missing warehouse record must never zero stock"


def test_refuses_when_too_many_skus_would_change():
    warehouse = [wh(f"S{i}", 99) for i in range(10)]
    storefront = [sf(f"S{i}", 1) for i in range(10)]
    plan = _mod().plan_sync(warehouse, storefront, max_change_ratio=0.30)
    assert _field(plan, "refused"), "100% of SKUs changing must trip the ratio guard"


def test_refuses_a_single_oversized_change():
    plan = _mod().plan_sync([wh("A", 10_000)], [sf("A", 1)], max_delta=500)
    assert _field(plan, "refused")


def test_refuses_a_negative_target():
    plan = _mod().plan_sync([wh("A", -5)], [sf("A", 10)])
    assert _field(plan, "refused")


def test_safe_plan_has_no_refusals():
    warehouse = [wh(f"S{i}", 10) for i in range(10)]
    storefront = [sf(f"S{i}", 10) for i in range(10)]
    storefront[0] = sf("S0", 9)
    plan = _mod().plan_sync(warehouse, storefront)
    assert _field(plan, "refused") == []


def test_planning_does_not_apply_anything():
    applier = Applier()
    _mod().plan_sync([wh("A", 12)], [sf("A", 5)])
    assert applier.calls == [], "planning must not touch the applier"


def test_apply_sync_calls_the_applier_once():
    mod = _mod()
    applier = Applier()
    plan = mod.plan_sync([wh("A", 12)], [sf("A", 5)])
    mod.apply_sync(plan, applier)
    assert len(applier.calls) == 1


def test_apply_sync_refuses_an_unsafe_plan():
    mod = _mod()
    applier = Applier()
    plan = mod.plan_sync([wh("A", 10_000)], [sf("A", 1)], max_delta=500)
    with pytest.raises(Exception):
        mod.apply_sync(plan, applier)
    assert applier.calls == [], "a refused plan must never reach the applier"


def test_undo_plan_restores_the_previous_quantity():
    plan = _mod().plan_sync([wh("A", 12)], [sf("A", 5)])
    undo = _field(plan, "undo")
    assert len(undo) == 1
    entry = undo[0]
    quantity = entry["quantity"] if isinstance(entry, dict) else getattr(entry, "quantity")
    assert quantity == 5, "undo must restore the storefront quantity observed at plan time"


def test_scales_linearly():
    import time

    warehouse = [wh(f"S{i}", 10) for i in range(50_000)]
    storefront = [sf(f"S{i}", 10) for i in range(50_000)]
    start = time.perf_counter()
    _mod().plan_sync(warehouse, storefront)
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, (
        f"took {elapsed:.1f}s — index both sides by SKU instead of scanning"
    )
''',
    },
    rubric=ENTERPRISE_RUBRIC,
)

# ---------------------------------------------------------------------------
# 7 — Incident report pipeline
# ---------------------------------------------------------------------------

INCIDENT_REPORT = ProjectSpec(
    slug="incident-report-pipeline",
    title="Incident Reporting — What The Postmortem Needs",
    tagline="Turn a month of on-call alerts into the numbers a postmortem review actually "
    "argues about.",
    level=SkillLevel.ENGINEERING,
    guidance=GuidanceLevel.INDEPENDENT,
    estimated_hours=6,
    xp_reward=480,
    concepts=("dictionaries", "sorting", "heaps", "complexity", "logging", "test-design"),
    prerequisites=("inventory-sync-service",),
    requirements="""\
## Business brief

You are handed a month of alert events from the on-call system and asked for the
numbers the monthly reliability review needs. There is no specification. There is
a review meeting on Friday and these are the questions people will ask:

- How many incidents, and how many were the *same* incident re-firing?
- Which service is worst — by count, and by total time in a bad state?
- What is our mean and median time to acknowledge, and to resolve?
- Which incidents breached the 15-minute acknowledgement SLA?
- When do incidents happen — is there a bad hour of the day?
- What are the top five noisiest alert rules, and what fraction of all alerts
  are they?

## Input

Events, in no particular order, possibly with duplicates:

```python
{"alert_id": "a1", "rule": "high-latency", "service": "orders",
 "severity": "critical", "state": "firing", "at": "2026-09-11T02:14:07Z"}
```

`state` is one of `firing`, `acknowledged`, `resolved`. An incident is a run of
events sharing an `alert_id`. Events may be missing: an alert can be resolved
without ever being acknowledged, and an alert may still be open at the end of the
window.

## What you must deliver

A module exposing `build_report(events, window_start, window_end, sla_minutes=15)`
returning a structure that answers every question above, plus a
`format_report(report)` producing something readable.

You choose everything else: the shapes, the module boundaries, the naming.

## Judgement, not just correctness

This project is assessed on the decisions you document as much as on the code.
Write them in the README:

- An incident that is still open at `window_end` — how does it count towards
  mean time to resolve? Excluding it flatters the numbers; counting it as
  resolved-now is a lie. Pick one, justify it, and make the report say which.
- Duplicate events — same `alert_id`, same `state`, same timestamp. Idempotent
  input is normal in alerting systems.
- Median with an even number of samples.
- Events outside the window, and events arriving out of order.
- An `acknowledged` that precedes its `firing` — a clock skew, which happens.

An engineer reading your report must be able to tell whether a number is
trustworthy. That is the actual deliverable.

## Constraints

- Standard library only.
- Linear in the number of events, except for sorts.
- Durations in whole seconds, computed from the timestamps, not floats of hours.
""",
    architecture_notes="""\
No architecture notes: this project is `independent`. Deciding the structure is
the work. What is worth knowing is what a reviewer will look for — a clear
separation between parsing events, assembling incidents, computing statistics and
formatting; statistics functions that take numbers rather than reaching into
incident objects; and a report structure that carries its own caveats rather than
relying on a human remembering them.
""",
    suggested_structure="",
    milestones=(
        {
            "key": "decide",
            "title": "Write the decisions down first",
            "detail": "Before any code, put your answers to the judgement questions in the "
            "README. They determine your data structures.",
        },
        {
            "key": "incidents",
            "title": "Events to incidents",
            "detail": "Group by alert_id, deduplicate, order by time, tolerate missing states.",
        },
        {
            "key": "stats",
            "title": "Statistics",
            "detail": "Mean and median acknowledge and resolve times, SLA breaches, per-service "
            "totals, hour-of-day distribution.",
        },
        {
            "key": "noise",
            "title": "Noisiest rules",
            "detail": "Top five by alert count, with their share of the total.",
        },
        {
            "key": "format",
            "title": "Format, with caveats",
            "detail": "A report a reviewer can trust, that states which numbers exclude open "
            "incidents.",
        },
    ),
    starter_files={
        "README.md": """\
# Incident Reporting

Independent project: no starter structure, no suggested modules.

Before you write code, answer these here, with reasons:

1. How do open incidents count towards mean time to resolve?
2. What happens to duplicate events?
3. How do you take a median of an even number of samples?
4. What happens to events outside the window, and out-of-order events?
5. What happens when `acknowledged` precedes `firing`?

Then build `build_report(events, window_start, window_end, sla_minutes=15)` and
`format_report(report)` in `incidents.py`.
"""
    },
    acceptance_tests={
        "test_acceptance_incidents.py": '''\
"""Acceptance tests: the minimum contract. Almost every design decision is yours.

These deliberately check less than the other projects. This is an independent
project: the rubric and a human reading your README carry most of the assessment.
"""

import pytest

START, END = "2026-09-01T00:00:00Z", "2026-10-01T00:00:00Z"


def _mod():
    return pytest.importorskip(
        "incidents",
        reason="create incidents.py exposing build_report() and format_report()",
    )


def ev(alert_id, state, at, rule="high-latency", service="orders", severity="critical"):
    return {
        "alert_id": alert_id, "rule": rule, "service": service,
        "severity": severity, "state": state, "at": at,
    }


def _get(report, *names):
    """Accept any reasonable naming for a required figure."""
    for name in names:
        if isinstance(report, dict) and name in report:
            return report[name]
        if hasattr(report, name):
            return getattr(report, name)
    raise AssertionError(f"the report must expose one of {names}")


FULL = [
    ev("a1", "firing", "2026-09-11T02:00:00Z"),
    ev("a1", "acknowledged", "2026-09-11T02:05:00Z"),
    ev("a1", "resolved", "2026-09-11T02:35:00Z"),
]


def test_builds_a_report():
    report = _mod().build_report(FULL, START, END)
    assert report is not None


def test_counts_one_incident():
    report = _mod().build_report(FULL, START, END)
    assert _get(report, "incident_count", "incidents_total", "total_incidents") == 1


def test_groups_repeated_alert_ids_into_one_incident():
    events = FULL + [
        ev("a1", "firing", "2026-09-11T03:00:00Z"),
        ev("a1", "resolved", "2026-09-11T03:10:00Z"),
    ]
    report = _mod().build_report(events, START, END)
    count = _get(report, "incident_count", "incidents_total", "total_incidents")
    assert count == 1, "events sharing an alert_id are one incident, however many times it fires"


def test_duplicate_events_do_not_double_count():
    report = _mod().build_report(FULL + FULL, START, END)
    assert _get(report, "incident_count", "incidents_total", "total_incidents") == 1


def test_reports_acknowledge_and_resolve_durations():
    report = _mod().build_report(FULL, START, END)
    ack = _get(report, "mean_ack_seconds", "mean_time_to_acknowledge_seconds", "mean_ack")
    res = _get(report, "mean_resolve_seconds", "mean_time_to_resolve_seconds", "mean_resolve")
    assert ack == pytest.approx(300, abs=1), "05:00 minus 02:00 is 300 seconds"
    assert res == pytest.approx(2100, abs=1), "35:00 minus 02:00 is 2100 seconds"


def test_flags_an_sla_breach():
    slow = [
        ev("b1", "firing", "2026-09-12T02:00:00Z"),
        ev("b1", "acknowledged", "2026-09-12T02:40:00Z"),
    ]
    report = _mod().build_report(slow, START, END, sla_minutes=15)
    breaches = _get(report, "sla_breaches", "breaches", "sla_breach_count")
    count = breaches if isinstance(breaches, int) else len(breaches)
    assert count == 1


def test_does_not_flag_a_fast_acknowledgement():
    report = _mod().build_report(FULL, START, END, sla_minutes=15)
    breaches = _get(report, "sla_breaches", "breaches", "sla_breach_count")
    count = breaches if isinstance(breaches, int) else len(breaches)
    assert count == 0


def test_reports_per_service_figures():
    events = FULL + [
        ev("c1", "firing", "2026-09-13T02:00:00Z", service="billing"),
        ev("c1", "resolved", "2026-09-13T02:10:00Z", service="billing"),
    ]
    report = _mod().build_report(events, START, END)
    services = _get(report, "by_service", "services", "per_service")
    assert len(services) == 2


def test_reports_noisiest_rules():
    events = []
    for i in range(7):
        events += [
            ev(f"n{i}", "firing", f"2026-09-14T0{i}:00:00Z", rule="flapping-disk"),
            ev(f"n{i}", "resolved", f"2026-09-14T0{i}:30:00Z", rule="flapping-disk"),
        ]
    events += FULL
    report = _mod().build_report(events, START, END)
    noisiest = _get(report, "noisiest_rules", "top_rules", "noisy_rules")
    assert len(noisiest) >= 1
    first = noisiest[0]
    name = first.get("rule") if isinstance(first, dict) else getattr(first, "rule", first)
    assert "flapping-disk" in str(name)


def test_handles_an_incident_that_never_resolved():
    open_incident = [ev("d1", "firing", "2026-09-15T02:00:00Z")]
    report = _mod().build_report(open_incident, START, END)
    assert report is not None, "an unresolved incident must not crash the report"


def test_handles_an_incident_resolved_without_acknowledgement():
    events = [
        ev("e1", "firing", "2026-09-16T02:00:00Z"),
        ev("e1", "resolved", "2026-09-16T02:20:00Z"),
    ]
    report = _mod().build_report(events, START, END)
    assert report is not None


def test_handles_out_of_order_events():
    shuffled = [FULL[2], FULL[0], FULL[1]]
    report = _mod().build_report(shuffled, START, END)
    ack = _get(report, "mean_ack_seconds", "mean_time_to_acknowledge_seconds", "mean_ack")
    assert ack == pytest.approx(300, abs=1), "input order must not change the result"


def test_empty_input_produces_a_report_not_a_crash():
    report = _mod().build_report([], START, END)
    assert _get(report, "incident_count", "incidents_total", "total_incidents") == 0


def test_format_report_returns_text():
    mod = _mod()
    output = mod.format_report(mod.build_report(FULL, START, END))
    assert isinstance(output, str) and output.strip()


# Deliberately no test that the README documents the judgement calls. The
# starter README already contains the words such a test would grep for, so it
# would pass before the learner had written anything — a vacuous check is worse
# than none. The `documentation` key in the rubric is what assesses this, and a
# human reading the reasoning is the only thing that actually can.
''',
    },
    rubric=ENTERPRISE_RUBRIC,
)

REAL_WORLD_PROJECTS: tuple[ProjectSpec, ...] = (
    LOG_ANALYZER,
    CSV_REPORT_ENGINE,
    API_CLIENT_SDK,
    INVOICE_RECONCILIATION,
    ETL_PIPELINE,
    INVENTORY_SYNC,
    INCIDENT_REPORT,
)
