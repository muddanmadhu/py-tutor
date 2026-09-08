# Deploying to GitHub Pages + Firebase

The topology this repository is configured for:

```
        ┌──────────────────────────┐
        │   GitHub Pages (free)    │  the React bundle, built by CI
        │  <user>.github.io/Py-Tutor│
        └────────────┬─────────────┘
                     │
        ┌────────────┴─────────────┐
        │                          │
┌───────▼─────────┐      ┌─────────▼──────────┐
│ Pyodide (WASM)  │      │  Cloud Run (API)   │  FastAPI, scales to zero
│ in the browser  │      │  + Firebase Auth   │  verifies Firebase ID tokens
│ runs the Python │      │  + Neon Postgres   │  free serverless Postgres
└─────────────────┘      └────────────────────┘
```

Learner code never reaches the server. That is what makes this deployable on
infrastructure that cannot run containers, and what keeps the bill at roughly
zero.

## What each piece costs

| Piece | Tier | Cost |
| --- | --- | --- |
| GitHub Pages | Public repository | Free |
| Cloud Run | 2M requests/month, scales to zero | Free in practice |
| Neon Postgres | Free tier | Free |
| Firebase Auth | 50k monthly active users | Free |
| Pyodide | Served from jsDelivr | Free |

Cloud Run requires the **Blaze** billing plan — a card on file — even while you
stay inside the free tier. Cloud SQL is *not* used here precisely because it has
no free tier; Neon replaces it.

---

## 1. Database — Neon

Create a project at <https://neon.tech> and copy the connection string. Convert
it to the driver this application uses by replacing the scheme:

```
postgresql://user:pw@ep-x.region.aws.neon.tech/db?sslmode=require
       ↓
postgresql+psycopg://user:pw@ep-x.region.aws.neon.tech/db?sslmode=require
```

Keep `?sslmode=require`. Neon refuses plaintext connections.

## 2. Identity — Firebase Auth

In the [Firebase console](https://console.firebase.google.com):

1. Create a project (or reuse one).
2. **Authentication → Sign-in method → Email/Password → Enable.**
3. **Authentication → Settings → Authorized domains →** add
   `<user>.github.io`. Sign-in is refused from unlisted origins.
4. **Project settings → Your apps → Web app** → copy the config values.

The server needs only the project id. It verifies ID tokens against Google's
published JWKS, so there is no service-account key to mount or rotate.

> Sign-in is email and password only. `frontend/src/state/firebase.ts` talks to
> the Firebase REST API rather than the `firebase` npm SDK, which keeps ~200 kB
> out of the bundle but leaves out the OAuth popup flow. Adding Google sign-in
> means installing the SDK and replacing that one file.

## 3. API — Cloud Run

```bash
gcloud run deploy pyforge-api \
  --source ./backend \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "PYFORGE_ENV=production,PYFORGE_DEBUG=false,PYFORGE_LOG_JSON=true" \
  --set-env-vars "PYFORGE_EXECUTOR=client" \
  --set-env-vars "PYFORGE_FIREBASE_PROJECT_ID=<firebase-project-id>" \
  --set-env-vars "PYFORGE_CORS_ORIGINS=https://<user>.github.io" \
  --set-secrets  "PYFORGE_SECRET_KEY=pyforge-secret:latest" \
  --set-secrets  "PYFORGE_DATABASE_URL=pyforge-db-url:latest"
```

Four of those matter more than the rest:

- **`PYFORGE_EXECUTOR=client`** — Cloud Run cannot launch sibling containers, so
  there is no server-side sandbox. This tells the API to grade from the result
  the browser reports. Without it the API boots and then fails every submission.
- **`PYFORGE_CORS_ORIGINS`** — the exact Pages origin, no trailing slash and no
  wildcard. A wildcard refuses to boot.
- **`PYFORGE_SECRET_KEY`** — from Secret Manager, and stable across revisions.
- **`PYFORGE_FIREBASE_PROJECT_ID`** — switches bearer-token verification from
  this application's own tokens to Firebase ID tokens.

`--allow-unauthenticated` is about Cloud Run's own IAM layer, not the
application: the API still requires a valid Firebase token on every protected
route.

### Migrate and seed

Run once per release, before the new revision takes traffic:

```bash
gcloud run jobs create pyforge-migrate \
  --image <the image Cloud Run just built> \
  --region europe-west1 \
  --set-secrets "PYFORGE_DATABASE_URL=pyforge-db-url:latest" \
  --set-env-vars "PYFORGE_ENV=production,PYFORGE_EXECUTOR=client,PYFORGE_DEBUG=false" \
  --command alembic --args upgrade,head

gcloud run jobs execute pyforge-migrate --region europe-west1
```

Then seed the curriculum the same way with
`python -m app.db.init_db --seed`. Seeding upserts by slug, so it is safe on
every deploy and is how curriculum updates ship.

## 4. Web app — GitHub Pages

In the repository, **Settings → Pages → Source → GitHub Actions**.

Then **Settings → Secrets and variables → Actions → Variables**, and add:

| Variable | Value |
| --- | --- |
| `VITE_API_BASE_URL` | `https://pyforge-api-xxxx.run.app` |
| `VITE_FIREBASE_API_KEY` | from the Firebase web config |
| `VITE_FIREBASE_AUTH_DOMAIN` | `<project>.firebaseapp.com` |
| `VITE_FIREBASE_PROJECT_ID` | `<project>` |
| `VITE_FIREBASE_APP_ID` | from the Firebase web config |

Variables, not secrets: all of these end up in a public bundle, and marking them
secret would only hide them from you. None of them authorise anything on their
own.

Pushing to `main` now builds and publishes
[`.github/workflows/pages.yml`](../.github/workflows/pages.yml).

### Two things the workflow does that are easy to miss

**`base: '/Py-Tutor/'`** in `vite.config.ts`. A project page is served from a
sub-path, so every asset URL needs the repository name in front of it. The
router reads the same value through `import.meta.env.BASE_URL`, so the two can
never disagree. Serving from a user page or a custom domain instead means
building with `--base=/`.

**`cp dist/index.html dist/404.html`.** Pages has no rewrite rules. A deep link
like `/Py-Tutor/learn/loops` is not a file on disk, so Pages serves `404.html` —
making that a copy of the entry point boots the app and lets the router resolve
the URL. The response still carries a 404 status, which browsers ignore and
crawlers do not; that is the accepted cost of SPA routing on Pages.

---

## Consequences of running the sandbox in the browser

These are real trade-offs, not oversights.

**Grading input is forgeable.** The browser reports what the code printed and
the server grades that report. Anyone can post a passing result with devtools.
The only person they cheat is themselves, which is why it is acceptable here —
but it means this deployment must never be used for graded assessment that
anything depends on. `SubmissionService.submit` honours a reported result *only*
when `PYFORGE_EXECUTOR=client`, so a Docker deployment is unaffected.

**Hidden tests are not hidden.** A pytest-graded exercise cannot run in the
browser without its test suite, so `ExecutionPlan.extra_files` ships it to the
client. It is readable in the network tab. Exercises whose value depends on the
tests being secret should use the `static_assert` grader, which never leaves the
server.

**First run is slow.** Pyodide is a multi-megabyte download plus a WASM boot.
The editor starts warming it on mount so the learner is reading the prompt while
it loads, and the first run gets a 60-second grace on top of the normal 10-second
timeout. Later runs reuse the interpreter and are fast.

**Timeouts kill the interpreter.** Pyodide cannot interrupt a synchronous
infinite loop from inside itself, so the only way to stop one is to terminate
the worker — which destroys the interpreter with it. The run after a timeout
therefore pays the boot cost again. This is why execution lives in a worker at
all: on the main thread a runaway loop would freeze the tab.

**Only pure-Python packages are available.** The sandbox has the standard
library and pytest. Anything requiring a native extension will not import.

## Rollback

The web app and the API roll back independently.

- **Web app**: re-run the Pages workflow from an earlier commit
  (Actions → Deploy web app → Run workflow), or revert and push.
- **API**: `gcloud run services update-traffic pyforge-api --to-revisions <old>=100`.
- **Database**: only if the release contained a destructive migration. Keep
  migrations additive — add nullable, backfill, tighten later — and this stays
  unnecessary. `0002_firebase_identity` is additive and guards itself with an
  inspection, so it is safe to re-run.
