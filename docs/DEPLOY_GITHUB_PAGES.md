# Publishing to GitHub Pages

The site is **fully static**. There is no backend, no database, no accounts and
nothing to pay for or operate.

```
                 GitHub Pages
  muddanmadhu.github.io/py-tutor
                      │
      ┌───────────────┼────────────────┐
      │               │                │
 content/*.json   Pyodide (WASM)   localStorage
 pre-rendered     runs Python,     progress, XP,
 from the real    grades, reviews  streak, mastery
 API at build
```

Everything happens in the visitor's browser. Python runs there, submissions are
graded there, and progress is kept there.

## How it works

**Content** — `tools/export_static.py` seeds a throwaway database, drives the
real FastAPI app through `TestClient`, and writes every GET response to a JSON
file. With no accounts, every read is a pure function of the seed curriculum, so
this is exact rather than an approximation, and the response shapes stay
identical to the API-backed mode. Output is ~63 files / ~300 KiB, generated in CI
and never committed, so it cannot drift from the curriculum.

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

## Publishing it

1. **Settings → Pages → Source → GitHub Actions.** That is the only setting
   needed; there are no secrets or variables to configure.
2. Push to `main`.

[`.github/workflows/pages.yml`](../.github/workflows/pages.yml) installs the
backend, runs the exporter, type-checks, lints, builds, and deploys. It also
asserts the content tree reached `dist/` — a build that ships without it looks
fine and then shows an empty curriculum to every visitor.

### Two things that are easy to get wrong

**The base path is case-sensitive.** `vite.config.ts` sets
`base: '/py-tutor/'`, which must match the repository name exactly. The router
reads the same value via `import.meta.env.BASE_URL`, so the two cannot disagree.
For a user page or a custom domain, build with `--base=/`.

**`404.html` is the SPA fallback.** Pages has no rewrite rules, so a deep link
like `/py-tutor/learn/loops` is not a file and Pages serves `404.html`. Making
that a copy of `index.html` boots the app and lets the router resolve the URL.
The response still carries a 404 status, which browsers ignore.

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
