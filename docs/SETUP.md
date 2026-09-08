# Setup Guide

## Fastest path: `./run-local.sh`

One command, no Docker. It creates the virtualenv, installs backend and frontend
dependencies, writes a `.env` with a fresh signing key, seeds the curriculum, and
starts both servers.

```bash
./run-local.sh
```

| Service | URL |
| --- | --- |
| Web app | <http://localhost:5173> |
| API docs | <http://127.0.0.1:8000/docs> |
| Health | <http://127.0.0.1:8000/health> |

Demo login: `learner@example.com` / `demo-password-123`.

Override the ports with `API_PORT=8100 WEB_PORT=5200 ./run-local.sh`.

**This path uses `PYFORGE_EXECUTOR=subprocess`**, which runs learner code on your
host without container isolation. That is fine for exploring alone; it is not
fine for anything anyone else can reach. Use Docker below for real isolation —
and note that `PYFORGE_ENV=production` refuses to start with this executor.

## With Docker (required in production)

Requirements: Docker 24+ with Compose v2, and `make`.

```bash
git clone <repository> pyforge && cd pyforge
cp .env.example .env

# Generate a real signing key and put it in .env
python -c "import secrets; print('PYFORGE_SECRET_KEY=' + secrets.token_urlsafe(48))"

make up      # builds the runner image, then starts db, redis, api and web
make seed    # loads the seed curriculum
```

| Service | URL |
| --- | --- |
| Web app | <http://localhost:5173> |
| API | <http://localhost:8000> |
| Interactive API docs | <http://localhost:8000/docs> |
| Health | <http://localhost:8000/health> |
| Readiness (incl. sandbox) | <http://localhost:8000/ready> |

Create a demo learner if you want to skip registration:

```bash
docker compose exec api python -m app.db.init_db --seed --demo
# learner@example.com / demo-password-123
```

Check that the sandbox is genuinely isolated:

```bash
curl -s localhost:8000/api/execution/health -H "Authorization: Bearer <token>" | jq
# {"backend": "docker", "healthy": true, "isolated": true, ...}
```

If `isolated` is `false`, learner code is running without container isolation.
Fix that before letting anyone else use the instance.

## Without Docker (local development)

You will not get container isolation this way. It is fine for working on the
curriculum, the API or the UI; it is not fine for exposing to anyone else.

### Backend

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -e "backend[dev,ai]"

export PYFORGE_ENV=development
export PYFORGE_DATABASE_URL="sqlite+pysqlite:///./pyforge.db"
export PYFORGE_EXECUTOR=subprocess         # DEV ONLY — no isolation
export PYFORGE_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"

cd backend
.venv/bin/python -m app.db.init_db --seed --demo
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

### Building just the runner image

Even in local development, build the runner image once so you can switch to real
isolation with a single environment variable:

```bash
docker build -t pyforge/runner:latest ./runner
export PYFORGE_EXECUTOR=docker
```

## Configuration

Every setting is an environment variable prefixed `PYFORGE_`; see
`.env.example` for the annotated list. The ones that matter most:

| Variable | Default | Notes |
| --- | --- | --- |
| `PYFORGE_ENV` | `development` | `production` enables the safety invariants |
| `PYFORGE_SECRET_KEY` | random per process | **Must** be set and stable in production, or every restart invalidates all tokens |
| `PYFORGE_DATABASE_URL` | SQLite file | PostgreSQL required in production |
| `PYFORGE_EXECUTOR` | `docker` | `subprocess` is refused in production |
| `PYFORGE_EXEC_TIMEOUT_SECONDS` | `10` | Raise for project acceptance suites, not for lessons |
| `PYFORGE_ANTHROPIC_API_KEY` | empty | Empty means the deterministic offline tutor |
| `PYFORGE_LOG_JSON` | `false` | `true` in production for structured logs |

## Verifying the installation

```bash
make test                     # backend unit + integration suite
make runner-image             # build the sandbox image
cd backend && pytest -m docker -v   # prove the isolation claims
make e2e                      # Playwright, against a running stack
```

`pytest -m docker` is the one to run after any change to the execution engine.
It asserts that network access fails, that the root filesystem is read-only, that
the process runs as UID 5000, that memory caps bite and that containers are
cleaned up.

## Common problems

**`/ready` reports `execution_engine: false`**
The runner image is missing or the daemon is unreachable. Run
`make runner-image`, and confirm `docker image inspect pyforge/runner:latest`
succeeds from inside the API container.

**Submissions fail with "the execution engine is offline"**
Same cause. On Linux, also check that the API container's user can read
`/var/run/docker.sock`.

**Every restart logs everyone out**
`PYFORGE_SECRET_KEY` is unset, so a random key is generated per process. Set it.

**Refusing to start: "Unsafe production configuration"**
Working as designed. The message lists exactly which invariants failed; fix them
rather than lowering `PYFORGE_ENV`.

**`pytest` collects nothing**
Run it from `backend/`; `testpaths` is relative to that directory.

**Monaco does not load**
The editor is a lazily-loaded chunk. Check the browser console for a blocked
request, and remember the strict CSP applies to the API's own responses, not to
the Vite dev server.

## Restricted environments (no Docker, no ports, locked-down network)

The application has been verified running under all three restrictions. What
works and what does not:

| Restriction | Effect | Workaround |
| --- | --- | --- |
| No Docker | `make up` unavailable; no container isolation | `PYFORGE_EXECUTOR=subprocess` (dev only — see `docs/SECURITY.md`) |
| Sockets cannot be bound | uvicorn cannot expose a port; the app itself still starts | Drive the real ASGI app in-process: `python ../tools/drive_api.py` |
| Package registry behind a proxy | `pip`/`npm` fail with `EPERM` or an idle timeout | Point the client at the *working* proxy — check for a stale `proxy` in `~/.npmrc` that disagrees with `HTTP_PROXY` |

Two diagnostics that need no dependencies at all:

```bash
python3 -m compileall -q backend/app runner   # syntax gate, works on Python 3.9
python3 tools/drive_runner.py                 # exercises the sandbox supervisor
```

`tools/drive_api.py` walks the full learner journey — register, lesson, sandbox
run, timeout, hint ladder, grading, mastery movement, code review, search,
dashboard, certification gating, tutor policy — against the real application and
the seeded database, and exits non-zero if any step misbehaves. It is the
fastest way to confirm a deployment is genuinely working.
