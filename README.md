# PyForge — Python Engineering Mastery Platform

A browser-based *Python Engineering University*: an interactive tutor, sandboxed code
execution engine, adaptive mastery model, AI mentor, project academy and professional
code-review engine in one application.

PyForge is **not** a tutorial website. Learners spend most of their time writing,
running, breaking and fixing Python inside the platform.

```
Absolute Beginner → Python Developer → Automation Developer
        → Backend/API Developer → Advanced Python Engineer → Production-Ready Developer
```

---

## Table of contents

| Doc | What it covers |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, layering, module boundaries |
| [docs/SETUP.md](docs/SETUP.md) | Getting it running (Docker & local) |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Day-to-day dev workflow, lint, format, migrations |
| [docs/API.md](docs/API.md) | REST API surface |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema, relationships, indexes |
| [docs/EXECUTION_ENGINE.md](docs/EXECUTION_ENGINE.md) | How learner code is run safely |
| [docs/SECURITY.md](docs/SECURITY.md) | Threat model and controls |
| [docs/TESTING.md](docs/TESTING.md) | Test strategy and pyramid |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Containers, CI/CD, production hardening |
| [docs/DEPLOY_GITHUB_PAGES.md](docs/DEPLOY_GITHUB_PAGES.md) | Publishing the static site (Render, Firebase, GitHub Pages) |
| [docs/CURRICULUM.md](docs/CURRICULUM.md) | Content model + how to author lessons |
| [docs/CURRICULUM_ROADMAP.md](docs/CURRICULUM_ROADMAP.md) | Curriculum expansion to ~300 hours: plan and progress |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Contribution guide |

---

## What's in the box

**Learning engine**
- Curriculum tree: Course → Module → Lesson → Concept → Exercise
- Every lesson follows the *Explain → Show → Execute → Experiment → Practice → Debug →
  Apply → Build → Test → Master* pattern
- Seed curriculum spanning fundamentals through APIs, testing and automation, plus a
  complete real-world project

**Execution**
- Docker-isolated Python runners: no network, read-only rootfs, CPU/memory/PID caps,
  wall-clock timeout, output truncation, automatic cleanup
- Multi-file projects, pytest runs, and stdin support

**Assessment**
- Deterministic graders: stdout match, pytest suites, static-analysis assertions
- Mastery engine with per-concept scores (accuracy, attempts, hints, latency, decay)
- Adaptive next-step recommendation and misconception targeting

**Mentoring**
- AI tutor with a strict *progressive hint ladder* — it will not hand over the solution
  while a learner is mid-exercise
- Senior-engineer code review across 11 dimensions

**Progress**
- Dashboard, streaks, XP, badges, certification gates tied to demonstrated mastery
- Learning analytics: drop-off points, hardest concepts, repeated mistakes

---

## Quickstart

**Static, no backend** (what the published site is — one command, nothing to install
beyond Node):

```bash
./serve-static.sh
# → http://localhost:4173/
```

Builds the bundle and serves it locally with the same SPA rewrite and cache headers
the production hosts use, so what you see locally is what visitors get. The
curriculum is pre-rendered JSON and Python runs in your browser under Pyodide —
no API, no database, no login. The AI chat tutor, accounts and certifications need
a server and are not in this mode;
[docs/DEPLOY_GITHUB_PAGES.md](docs/DEPLOY_GITHUB_PAGES.md) lists exactly what is left
out and why.

**Without Docker** (full feature set — no container isolation, dev only):

```bash
./run-local.sh
# → web app  http://localhost:5173/py-tutor/
# → API docs http://127.0.0.1:8000/docs
# → login    learner@example.com / demo-password-123
```

The script creates the virtualenv, installs both dependency sets, writes a
`.env` with a fresh signing key, seeds the curriculum, and starts the API and the
web app together. Ctrl-C stops both.

The `/py-tutor/` path is Vite's `base`, set so the published GitHub Pages project
page resolves its assets; the dev server honours it too. Publishing needs no
server at all — see
[docs/DEPLOY_GITHUB_PAGES.md](docs/DEPLOY_GITHUB_PAGES.md).

**With Docker** (real container isolation — required in production):

```bash
cp .env.example .env
make up            # postgres + redis + api + runner image + web
make seed          # load the seed curriculum
open http://localhost:5173/py-tutor/
```

API docs: <http://localhost:8000/docs>

Full instructions, including restricted environments, are in
[docs/SETUP.md](docs/SETUP.md).

---

## Repository layout

```
.
├── backend/            FastAPI application (API, domain, persistence, execution)
│   ├── app/
│   │   ├── api/        HTTP layer — routers, dependencies, error handling
│   │   ├── core/       Config, logging, security primitives
│   │   ├── db/         Engine, session, bootstrap
│   │   ├── models/     SQLAlchemy ORM models
│   │   ├── schemas/    Pydantic request/response contracts
│   │   ├── services/   Application + domain services (mastery, grading, AI, review)
│   │   ├── execution/  Sandboxed Python execution engine
│   │   └── content/    Seed curriculum, reference, projects, interview bank
│   └── tests/          unit + integration tests (pytest)
├── runner/             Hardened Python runner image
├── frontend/           React + TypeScript + Vite + Monaco
├── e2e/                Playwright end-to-end suite
├── tools/              Developer utilities (see docs/DEVELOPMENT.md)
└── docs/               Full documentation set
```

---

## Definition of done

A new user can register, follow a learning path, read a lesson, write and safely execute
Python, get output and errors explained, receive progressive hints, submit exercises, be
graded, watch mastery move, be routed adaptively, build projects, search the reference,
converse with the AI tutor, debug broken programs, write tests, receive a code review,
and finish with a real-world capstone assessed against an engineering rubric.

See [docs/TESTING.md](docs/TESTING.md) for how each of those is covered by tests.
