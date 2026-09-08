# Deployment Guide

## The path from laptop to production

```
Local Python
      ↓        virtualenv, SQLite, subprocess executor
Virtual environment
      ↓        pip install -e ".[dev]"
Package
      ↓        pyproject.toml, pinned resolution
Docker
      ↓        backend/Dockerfile + runner/Dockerfile
CI/CD
      ↓        lint → type-check → test → migrate → build → deploy
Production
             PostgreSQL, Redis, isolated runners, structured logs
```

## Pre-flight checklist

Do not deploy without every one of these:

- [ ] `PYFORGE_ENV=production`
- [ ] `PYFORGE_SECRET_KEY` — unique, 32+ characters, from a secrets manager, and
      **stable across restarts** (a new key logs everyone out)
- [ ] `PYFORGE_DATABASE_URL` — PostgreSQL, TLS enforced
- [ ] `PYFORGE_EXECUTOR=docker` — or `client` where the host cannot run
      containers, which moves the sandbox into the browser; `subprocess` is
      refused either way
- [ ] `PYFORGE_CORS_ORIGINS` — exact origins, never `*`
- [ ] `PYFORGE_LOG_JSON=true`
- [ ] `PYFORGE_DEBUG=false`
- [ ] Runner image built and available to the API host (Docker executor only)
- [ ] `alembic upgrade head` run against the target database
- [ ] TLS terminated in front of the API; HSTS confirmed
- [ ] Database backups configured *and a restore tested*
- [ ] Alerting on `/ready` returning `degraded`

`Settings._enforce_production_invariants` refuses to boot if the first six are
wrong. Failing to start is the correct behaviour — a platform silently running
unisolated code with a default signing key is worse than one that is down.

> Deploying to GitHub Pages, Firebase Auth and Cloud Run instead? That topology
> has no server-side sandbox and its own set of trade-offs; see
> [DEPLOY_GITHUB_PAGES.md](DEPLOY_GITHUB_PAGES.md).

## Images

**API** (`backend/Dockerfile`): `python:3.12-slim`, non-root UID 5001, includes
the Docker CLI so it can launch sibling runners.

**Runner** (`runner/Dockerfile`): `python:3.12-slim` plus pytest and one
supervisor script. Non-root UID 5000. No package manager at runtime.

Build and publish both, tagged with the release:

```bash
docker build -t registry.example.com/pyforge/api:1.2.3 ./backend
docker build -t registry.example.com/pyforge/runner:1.2.3 ./runner
docker push registry.example.com/pyforge/api:1.2.3
docker push registry.example.com/pyforge/runner:1.2.3
```

The runner tag must be pinned via `PYFORGE_RUNNER_IMAGE`. Do not use `:latest` in
production: a runner image that changes underneath a running API changes what
learner code can do.

**Frontend**: build static assets and serve them from a CDN or an Nginx sidecar.

```bash
cd frontend && VITE_API_BASE_URL=https://api.example.com npm run build
# dist/ is a static bundle
```

## Migrations

```bash
docker run --rm \
  -e PYFORGE_DATABASE_URL="$DATABASE_URL" \
  -e PYFORGE_SECRET_KEY="$SECRET_KEY" \
  -e PYFORGE_ENV=production \
  registry.example.com/pyforge/api:1.2.3 \
  alembic upgrade head
```

Run migrations as a separate step **before** rolling out the new API, and keep
each release's migrations backwards-compatible with the previous version's code
so a rollback does not require a database restore. In practice: add columns as
nullable, backfill, then tighten in a later release.

## Seeding content

Seeding is idempotent — it upserts by slug — so it is safe to run on every
deploy, and it is how curriculum updates ship:

```bash
docker run --rm -e PYFORGE_DATABASE_URL="$DATABASE_URL" ... \
  registry.example.com/pyforge/api:1.2.3 \
  python -m app.db.init_db --seed
```

Learner progress is keyed on database ids that the upsert preserves, so
re-seeding never destroys someone's work. Authored hint ladders *are* replaced
wholesale, because they are content rather than user data.

## Runtime topology

### Single host (small deployment)

`docker-compose.yml` as shipped: db, redis, api, web, with the API mounting the
Docker socket to launch runners.

**The Docker socket is equivalent to root on the host.** Acceptable for a
single-tenant instance you control; not acceptable for a hostile multi-tenant one.

### Recommended (isolated runners)

```
            ┌─────────────┐
  Internet  │   Ingress   │  TLS, HSTS, rate limiting
            └──────┬──────┘
        ┌──────────┴──────────┐
        │                     │
 ┌──────▼──────┐      ┌───────▼────────┐
 │  Web (CDN)  │      │  API replicas  │  stateless, /health + /ready
 └─────────────┘      └───┬────────┬───┘
                          │        │
              ┌───────────▼──┐  ┌──▼─────────────────┐
              │  PostgreSQL  │  │  Runner service    │
              │  + Redis     │  │  own pool, no DB   │
              └──────────────┘  │  access, mTLS only │
                                └────────────────────┘
```

The runner service exposes exactly one operation ("run this job"), holds no
credentials for anything else, and can be swapped for gVisor, Firecracker or
Kubernetes Jobs without the API changing. `app/execution/factory.py` is the seam.

### Kubernetes notes

The application is already Kubernetes-shaped: configuration entirely from the
environment, stateless API, `/health` for liveness and `/ready` for readiness.
What you must add:

* a `Secret` for `PYFORGE_SECRET_KEY`, the database URL and the AI key
* resource requests/limits on the API (execution is bounded separately)
* a `NetworkPolicy` denying egress from runner pods
* a migration `Job` in a pre-deploy hook
* `topologySpreadConstraints` if you run more than a couple of replicas

## Multi-replica caveats

Two things are in-process today and must move before scaling horizontally:

| Component | Today | Change |
| --- | --- | --- |
| `ExecutionRateLimiter` | Per-process sliding window | Redis sorted set keyed on user id |
| Execution semaphore | Per-process | Runner service with its own queue |

Both are single classes. Until then, either run one API replica or accept that
the effective rate limit is *N × the configured value*.

## Observability

Set `PYFORGE_LOG_JSON=true` and every line becomes one JSON object carrying the
correlation id, so a learner-reported failure is one query away:

```json
{"timestamp":"2026-09-06T09:14:22+0000","level":"INFO","logger":"app.access",
 "message":"POST /api/exercises/loops-fizzbuzz/submit -> 200",
 "correlation_id":"7f3c…","status_code":200,"duration_ms":842.1}
```

Worth alerting on:

| Signal | Why |
| --- | --- |
| `/ready` returns `degraded` | Database or sandbox unreachable — submissions are failing |
| 5xx rate | The unhandled-exception handler fired |
| `execution_unavailable` count | Runner pool saturated or the daemon is sick |
| p95 submission duration | Container start-up or the database degrading |
| Orphaned `pyforge.role=runner` containers | Cleanup is failing; the host will fill up |
| `ai_unavailable` count | Model outage or the daily cap being hit |

## Backup and recovery

* **Database**: managed automated backups plus point-in-time recovery. Test a
  restore on a schedule — an untested backup is a hypothesis.
* **Content**: lives in source control and is re-seedable, so it needs no backup.
* **Learner code**: inside `submissions`, `project_workspaces` and
  `lesson_progress.scratch_files`. This is the data people would actually miss.

RPO/RTO depend on the managed database tier; state them explicitly in your
runbook rather than assuming.

## Rollback

1. Re-deploy the previous API image tag.
2. Only roll the database back if the release contained a destructive migration —
   which is why migrations should be additive.
3. Runner images are independent; rolling the API back does not require rolling
   the runner back.

## Zero-downtime deploys

The API is stateless, so a rolling update works, provided:

* migrations are additive and applied before the rollout
* the previous version tolerates the new schema (it will, if migrations are
  additive)
* in-flight sandbox runs are allowed to finish — set
  `terminationGracePeriodSeconds` above `PYFORGE_EXEC_TIMEOUT_SECONDS` plus the
  container start-up guard
