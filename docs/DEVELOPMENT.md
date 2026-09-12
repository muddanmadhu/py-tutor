# Development Guide

## Daily loop

```bash
make dev-api        # uvicorn with reload on :8000
make dev-web        # vite on :5173
make test           # backend suite
make lint           # ruff + mypy + eslint + tsc
make check          # what CI runs on a pull request
```

Run `make check` before pushing. It is the same commands CI runs, so a green
local run means a green pipeline.

## Repository map

```
backend/app/
├── main.py            application factory, error handlers, health probes
├── core/              config, logging, security primitives, error taxonomy
├── db/                engine, session, bootstrap + seeding
├── models/            SQLAlchemy ORM entities and shared enums
├── schemas/           Pydantic request/response contracts
├── api/               routers, dependencies, middleware
├── services/          all behaviour — the part worth reading first
├── execution/         sandbox contracts and backends
└── content/           the authored curriculum
```

Start with `services/mastery.py` and `services/submissions.py`: between them they
explain how the platform actually works.

## Conventions

**Type hints everywhere.** `mypy --strict` runs on `app/` in CI. If a signature
is hard to type, that is usually a design smell rather than a typing problem.

**Docstrings that say why.** The linter enforces presence (`ruff` rule `D`); code
review enforces usefulness. A docstring restating the function name adds nothing;
one explaining a non-obvious decision saves the next reader an hour.

**Services take a `Session`, never open one.** Transaction boundaries belong to
the HTTP layer (`get_db`) or to a script (`session_scope`). This keeps "what is
atomic" visible at the edge instead of scattered.

**Errors are typed.** Raise something from `app.core.errors`; the handlers turn it
into the standard envelope. Never `raise HTTPException` from a service.

**No `os.environ` outside `core/config.py`.** One place reads the environment.

**Naming.** `snake_case` for functions and variables, `CapWords` for classes,
`SCREAMING_SNAKE` for module constants. Prefer a longer name that explains itself.

## Adding an API endpoint

1. Add the request/response schemas to `app/schemas/`.
2. Put the behaviour in a service — the router should be a thin adapter.
3. Add the route to a router in `app/api/v1/routers/`, with a `summary=` (it
   becomes the OpenAPI title) and a docstring (it becomes the description).
4. Write a service unit test and an API integration test.
5. Add the endpoint to `docs/API.md`.

A router function that contains business logic is the most common review comment
on this codebase.

## Adding curriculum content

See `docs/CURRICULUM.md`. In short: add a `LessonSpec` to a module in
`app/content/lessons/`, re-run `make seed`, and let the content tests tell you
what you forgot. `validate()` runs at import time, so a broken lesson fails
immediately rather than at seed time.

## Database changes

```bash
cd backend
# 1. change the model in app/models/
# 2. generate the migration
.venv/bin/alembic revision --autogenerate -m "add project workspace notes"
# 3. READ the generated file — autogenerate misses table/column renames and
#    sometimes gets server defaults wrong
# 4. apply, then verify it reverses
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
.venv/bin/alembic upgrade head
```

Always test the downgrade. CI runs `upgrade → downgrade base → upgrade`, so a
one-way migration fails the build.

Adding a column to a table with data needs a nullable column or a server default;
autogenerate will happily produce a `NOT NULL` with no default, which fails on a
non-empty table.

## Tests

```bash
pytest                              # everything except docker-marked tests
pytest tests/test_mastery.py -v     # one file
pytest -k "hint"                    # by name
pytest -m docker -v                 # container isolation (needs the daemon)
pytest --cov=app --cov-report=html  # coverage report in htmlcov/
```

The suite runs against SQLite with the subprocess executor, so it needs no
infrastructure and finishes in seconds. Anything requiring Docker or PostgreSQL is
marked and runs in its own CI job.

Fixtures live in `tests/conftest.py`:

| Fixture | Gives you |
| --- | --- |
| `session` | A fresh schema, one transaction |
| `seeded_session` | The same, plus the full curriculum |
| `client` / `seeded_client` | A `TestClient` sharing that session |
| `user` / `auth_headers` | A registered learner and their bearer header |
| `executor` | The configured execution backend |

## Debugging

**A failing submission.** Reproduce it as a service call in a test — you get the
real grader output without the HTTP layer in the way.

**A sandbox problem.** Run the runner by hand:

```bash
echo '{"mode":"script","entrypoint":"main.py","files":{"main.py":"print(1)"}}' \
  | docker run --rm -i --network none pyforge/runner:latest
```

**Tracing a request.** Every response carries `X-Correlation-ID`, and every log
line for that request carries the same id. `docker compose logs api | grep <id>`
reconstructs the whole story.

**SQL.** `PYFORGE_DATABASE_ECHO=true` logs every statement.

## Formatting and linting

```bash
make fmt      # ruff format + ruff --fix + prettier
make lint     # ruff check, ruff format --check, mypy, eslint, tsc
```

Ruff is configured in `backend/pyproject.toml`. The rule set includes `S`
(bandit security checks) and `D` (docstrings) deliberately. If a rule genuinely
does not apply, add a targeted `# noqa: RULE` with a reason — never a bare
`# noqa`.

## No-Python environments

If you are working on this without a Python 3.11+ interpreter available:

```bash
node tools/pylex-check.js backend runner   # lexes every .py: unterminated
                                           # strings, unbalanced brackets, tabs
python3 -m compileall -q backend/app runner   # real syntax gate; works on 3.9+
```

Neither substitutes for the test suite, but together they catch the errors that
content-heavy files with embedded source actually hit.

## Driving the sandbox without Docker

`tools/drive_runner.py` runs the container supervisor (`runner/entrypoint.py`)
against a temporary workspace instead of `/workspace`, so you can exercise the
job protocol and the safety guards on a laptop with **no dependencies at all** —
it is stdlib-only and runs on Python 3.9:

```bash
python3 tools/drive_runner.py
```

It covers: normal output, multi-file imports, stdin, traceback capture, the
timeout kill, output truncation, and a refused path escape. Anything needing
`pytest` is skipped when pytest is not installed.

This is how the `-I` isolated-mode defect was found: `-I` implies `-P`, which
drops the workspace from `sys.path`, so `from helper import shout` could never
resolve. The runner now uses `-s -E`, which keeps the same isolation without
breaking multi-file submissions.

## Checking the static build the way a host serves it

`./serve-static.sh` builds the no-backend bundle and serves it on :4173 through
`tools/static_server.mjs`, which reproduces the SPA rewrite and the cache and
security headers from `render.yaml`. Use it before publishing: routing bugs —
a deep link that 404s, a `content/` response served from cache — do not appear
under `vite dev`, which resolves those paths itself.

```bash
./serve-static.sh --rebuild        # export content, typecheck, lint, build, serve
node --test tools/static_server.test.mjs   # the routing rules
```

The server is Node stdlib only and binds nothing on import, so the test drives
the handler with mock request and response objects — a machine that forbids
listening sockets still runs the coverage.
