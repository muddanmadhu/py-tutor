# Publishing the static site

The site is **fully static**. There is no backend, no database, no accounts and
nothing to pay for or operate. Two hosts are set up; pick either.

|  | GitHub Pages | Firebase Hosting |
| --- | --- | --- |
| URL | `muddanmadhu.github.io/py-tutor/` | `<project>.web.app/` |
| Base path | `/py-tutor/` | none — serves from the root |
| Deep links | `404.html` fallback, 404 status | real rewrites, 200 status |
| Setup | one setting, then automatic on push | CLI login once, then one command |
| Cost | free (public repositories) | free — **Spark plan, no billing card** |

Firebase gives the cleaner URLs and correct status codes; Pages gives
deploy-on-push with no local tooling. Nothing stops you using both.

## Option A — GitHub Pages

1. **Settings → Pages → Source → GitHub Actions.**
2. Push to `main`.

That is the whole setup: no secrets, no variables.
[`.github/workflows/pages.yml`](../.github/workflows/pages.yml) installs the
backend, runs the exporter, type-checks, lints, builds, asserts the content tree
reached `dist/`, and deploys.

## Option B — Firebase Hosting

One-time, and it needs a browser so it cannot be scripted:

```bash
npm install -g firebase-tools
firebase login
firebase use --add        # pick your project; writes .firebaserc
```

Then, for every deploy:

```bash
./deploy-firebase.sh              # live
./deploy-firebase.sh --preview    # temporary URL, expires in 7 days
```

The script regenerates the content, type-checks, lints, builds with
`--base=/`, verifies the bundle, and deploys. To make it automatic on push
instead, `firebase init hosting:github` writes a workflow and stores the service
account for you.

Hosting is a static file server, so the **Spark** (free) plan is enough. Blaze is
only needed for Cloud Functions or Cloud Run, and this build uses neither.
[`firebase.json`](../firebase.json) sets the SPA rewrite, fingerprinted assets to
`immutable` for a year, and the content tree to `must-revalidate` — the latter
matters because those filenames are stable across deploys, so caching them would
pin visitors to an old curriculum.

## How it works

```
              static host
                   │
   ┌───────────────┼────────────────┐
   │               │                │
content/*.json  Pyodide (WASM)   localStorage
pre-rendered    runs Python,     progress, XP,
from the real   grades, reviews  streak, mastery
API at build
```

**Content** — `tools/export_static.py` seeds a throwaway database, drives the
real FastAPI app through `TestClient`, and writes every GET response to a JSON
file. With no accounts, every read is a pure function of the seed curriculum, so
this is exact rather than an approximation, and the response shapes stay
identical to the API-backed mode. Output is ~63 files / ~300 KiB, generated at
deploy time and never committed, so it cannot drift from the curriculum.

**Execution** — Pyodide, in a Web Worker. A worker rather than the main thread
because Pyodide cannot interrupt a synchronous infinite loop from inside itself;
terminating the worker is the only way to enforce a timeout.

**Grading** — the actual `app/services/grading.py`, shipped into Pyodide with its
four `app.*` imports replaced by shims. Reimplementing it in TypeScript would
fork the logic that decides whether a learner passed, and the `static_assert`
grader needs Python's own `ast` module anyway.
`backend/tests/test_static_grader.py` grades the same submissions through both
implementations and requires identical verdicts.

**Code review** — `app/services/code_review.py` runs unmodified. It imports only
`ast`, `re`, `dataclasses` and `enum`, so the whole 11-dimension review survives
having no server for the cost of copying a file.

**Mastery** — a port, in `frontend/src/static/mastery.ts`, because the Python
engine is bound to SQLAlchemy. `backend/tests/test_static_mastery.py` runs both
and requires the same numbers to 1e-9, so the port cannot drift silently.

**The content contract** — `backend/tests/test_static_export.py` asserts the
exported JSON actually carries every field the client reads. TypeScript cannot
catch that: a field can exist on an interface and be absent from the data, which
reads as `undefined` and shows up as an empty panel on the live site.

## What is not in the static build

Stated plainly, because the UI shows these states rather than hiding them:

| Feature | Why not |
| --- | --- |
| **AI chat tutor** | Needs a model API key. One in a public bundle is one anybody can spend. The hint ladder is available instead. |
| **Accounts** | Nothing to authenticate against. Everyone is the same anonymous local learner. |
| **Certifications** | Awarded on assessed project submissions against a rubric — a server judgement. Claiming would be theatre. |
| **Adaptive remediation** | The adaptive service weighs misconception data across learners, which one browser does not have. |
| **Prerequisite readiness** | Needs the concept graph's edges, which the concept export does not carry. |
| **Cross-device progress** | It lives in one browser's localStorage. Settings has an export/import so it can be moved by hand. |

## Consequences worth knowing

**Progress is not authoritative.** It is a JSON document in localStorage that its
owner can edit, and clearing site data erases it. That is acceptable because the
only person affected is its owner — but this build must never be used for graded
assessment that anything depends on.

**Hidden tests are not hidden.** A pytest-graded exercise cannot run in the
browser without its test suite, so it ships and is readable in the network tab.
Hints and reference solutions ship for the same reason. The UI still gates them
behind the hint ladder, which is now a courtesy rather than a control. Exercises
whose value depends on secrecy should use the `static_assert` grader.

**First run is slow.** Pyodide is a multi-megabyte download plus a WASM boot,
fetched from jsDelivr. The editor starts warming it on mount so the learner is
reading the prompt while it loads, and the first run gets a 60-second grace on
top of the normal 10-second timeout. Later runs reuse the interpreter.

**A timeout kills the interpreter.** Stopping a runaway loop means terminating
the worker, which destroys the interpreter with it, so the run after a timeout
pays the boot cost again.

**Only pure-Python packages work.** The sandbox has the standard library and
pytest. Anything needing a native extension will not import.

## Base paths, and why they differ

`vite.config.ts` defaults to `base: '/py-tutor/'`, which must match the
repository name exactly — Pages treats it case-sensitively. The router reads the
same value through `import.meta.env.BASE_URL`, and so does the content fetcher,
so nothing can disagree with the asset URLs.

Firebase serves from the domain root, so `npm run build:root` builds with
`--base=/` instead. `deploy-firebase.sh` uses it. A custom domain on either host
wants the root build too.

## Running it with the full feature set

The same codebase still runs API-backed, which is what `run-local.sh` does — with
the AI tutor, adaptive routing, certifications and server-side sandboxing:

```bash
./run-local.sh          # → http://localhost:5173/py-tutor/
```

Setting `VITE_API_BASE_URL` is what selects the API-backed implementation; its
absence selects the static one. `frontend/src/api/endpoints.ts` makes that choice
and asserts, at compile time, that both implementations expose the same surface —
so adding an endpoint to one and forgetting the other fails the build instead of
showing a blank page to whoever visits the published site.

For hosting the API somewhere real, see [DEPLOYMENT.md](DEPLOYMENT.md).
