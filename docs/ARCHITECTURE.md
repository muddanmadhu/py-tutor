# Architecture

## The shape of the system

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser — React + TypeScript + Monaco                               │
│  Dashboard · Learn · Practice · Projects · Reference · Lab · Tutor    │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTPS / JSON, bearer tokens
┌───────────────────────────────▼──────────────────────────────────────┐
│  API layer            app/api                                        │
│  Routers, dependencies, middleware, one error envelope               │
├──────────────────────────────────────────────────────────────────────┤
│  Application services app/services                                   │
│  auth · curriculum · exercises · submissions · progress · projects    │
│  mastery · adaptive · grading · code_review · ai_tutor · analytics    │
│  gamification · certification · search                               │
├──────────────────────────────────────────────────────────────────────┤
│  Domain model         app/models  +  app/content                     │
│  ORM entities, enums, the concept graph, the authored curriculum      │
├──────────────────────────────────────────────────────────────────────┤
│  Persistence          app/db          Execution   app/execution      │
│  SQLAlchemy 2.0, Alembic              Job validation + backends      │
└───────────────┬─────────────────────────────────┬────────────────────┘
                │                                 │
        ┌───────▼────────┐             ┌──────────▼──────────┐
        │  PostgreSQL    │             │  Runner containers  │
        │  Redis (cache) │             │  no net · ro fs ·   │
        └────────────────┘             │  capped cpu/mem/pid │
                                       └─────────────────────┘
```

## Layering rules

The dependency arrow points one way, and the codebase is arranged so that
violating it is obvious in a code review:

| Layer | May import | May **not** import |
| --- | --- | --- |
| `api/` | `services`, `schemas`, `models`, `core` | nothing above it |
| `services/` | `models`, `execution`, `core`, `db` | `api`, `schemas` (mostly) |
| `models/` | `db.base`, `models.enums` | `services`, `api` |
| `execution/` | `core` | `models`, `services`, `api` |
| `content/` | `content.schema`, `models.enums` | everything else |

Two consequences worth stating explicitly:

* **Services never touch HTTP.** They take a `Session` and plain arguments, so
  every one of them is unit-testable without a running server. The tests in
  `tests/test_mastery.py` and `tests/test_services.py` do exactly that.
* **The execution engine knows nothing about learners.** It validates a file set
  and runs it. Rate limiting, analytics and grading all sit above it, which is
  what lets the same engine serve the Code Lab, an exercise, and a project's
  acceptance tests.

## The eleven separated concerns

The specification asks for UI, auth, curriculum, learning engine, assessment,
execution, AI tutor, progress, projects and analytics to be separable. They map
onto modules like this:

| Concern | Module |
| --- | --- |
| UI | `frontend/` |
| Authentication | `app/services/auth.py`, `app/core/security.py` |
| Curriculum | `app/content/`, `app/services/curriculum.py` |
| Learning engine | `app/services/adaptive.py` |
| Assessment | `app/services/grading.py`, `app/services/submissions.py` |
| Code execution | `app/execution/`, `runner/` |
| AI tutor | `app/services/ai_tutor.py` |
| Progress tracking | `app/services/mastery.py`, `app/services/progress.py` |
| Project management | `app/services/projects.py` |
| Analytics | `app/services/analytics.py` |
| Gamification | `app/services/gamification.py`, `certification.py` |

## Request lifecycle

A submission is the most interesting path, because it touches nearly everything:

```
POST /api/exercises/{slug}/submit
  │
  ├─ CorrelationIdMiddleware      assigns an id, logs the request
  ├─ get_current_user             validates the bearer token
  ├─ get_db                       opens one transaction for the request
  │
  └─ SubmissionService.submit
       ├─ rate limiter            per-user sliding window
       ├─ build_job               validates paths, size, file count, entrypoint
       ├─ executor.run            disposable container: no net, capped, timed
       ├─ grading.grade           deterministic score + per-check breakdown
       ├─ MasteryService.record   folds the evidence into every concept
       ├─ gamification            XP (discounted by hints), streak, badges
       └─ analytics.record_event  appends to the event stream
  │
  └─ commit  (or roll back everything, including the analytics event)
```

Everything in that list shares one transaction. If the mastery update fails, the
submission is not recorded either — there is no state in which a learner has a
passing submission whose mastery was never counted.

## Key design decisions

### Sync SQLAlchemy, not async

FastAPI runs `def` endpoints in a thread pool, so the API is still concurrent.
Sync sessions buy simpler transaction semantics, work identically on SQLite and
PostgreSQL, and remove a category of "coroutine was never awaited" bugs. The
workload is dominated by sandbox execution (seconds) rather than by database
round-trips (milliseconds), so async ORM access would optimise the wrong thing.

### Content as typed Python, not YAML

`app/content/` is dataclasses validated at import time. A malformed lesson is a
startup failure with a precise message, not a mystery in production. Concept
slugs are *referenced*, so a typo is a `ContentError` rather than an orphaned
mastery record. See `docs/CURRICULUM.md`.

### Mastery decays on read

`ConceptMastery.score` is the stored estimate; the retention factor is applied
when it is read. A learner returning after a month sees an honest number without
a background job having rewritten every row in the table. The cost is that
`score` in the database is not directly comparable across learners with
different last-practised dates — which is why every read path goes through
`MasteryService.view_for`.

### Deterministic grading, advisory AI

The grade a learner receives never depends on a model. Graders are
`stdout_match`, `pytest`, `static_assert` and `multiple_choice`; the code review
engine is an AST walk. The AI tutor adds explanation and Socratic pressure on
top, and the platform degrades to a genuinely useful offline mode without it.
This is why the same submission always produces the same score, and why an API
outage cannot block a learner's progress.

### The hint ladder is server-side state

Which rung a learner has reached lives in `hint_reveals`, and the tutor's system
prompt is rebuilt from it on every turn. A learner cannot talk the tutor into
skipping ahead, because the instruction to withhold is not in the conversation
they can influence.

### Sibling containers, not privileged execution

The API launches runner containers through the host Docker socket. That socket
is powerful, and mounting it is the main trade-off in this design — see
`docs/SECURITY.md` for the threat model and the production alternative (a remote
runner service with a narrow, authenticated API).

## Scaling path

The architecture is deliberately boring so that it can grow in obvious steps:

| Pressure | Change |
| --- | --- |
| More concurrent runs | Move execution behind a queue (Redis + workers); the `Executor` protocol already isolates this |
| Search outgrows the corpus | Replace `SearchService` scoring with PostgreSQL `tsvector` + `pg_trgm`; the interface is one method |
| Many API replicas | Move the in-process rate limiter to Redis (`ExecutionRateLimiter` is one class) |
| Multi-region | The API is stateless; only the database and the runner pool are not |
| Kubernetes | Each container already takes all configuration from the environment and exposes `/health` and `/ready` |

## What is deliberately not here

* **No microservices.** One deployable API. The seams are module boundaries, and
  they are enforced by the import rules above. Splitting them into services is a
  deployment decision to make when there is a reason, not before.
* **No event sourcing.** `learning_events` is an append-only analytics stream,
  but it is not the source of truth for state.
* **No caching layer in front of content.** Redis is configured and available;
  the curriculum is small enough that adding a cache now would be complexity
  without a measured benefit.
