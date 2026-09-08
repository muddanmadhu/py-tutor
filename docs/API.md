# API Reference

Base URL: `http://localhost:8000`, prefix `/api`.
Interactive documentation (generated from the code): `/docs` and `/redoc`.

## Conventions

**Authentication.** `Authorization: Bearer <access_token>`. Access tokens last 30
minutes; exchange the refresh token at `/api/auth/refresh`.

**Errors.** Every non-2xx response has this shape:

```json
{
  "error": {
    "code": "exercise_not_found",
    "message": "Exercise 'foo' was not found.",
    "details": {"resource": "Exercise", "identifier": "foo"},
    "correlation_id": "0f2c9a1b4e..."
  }
}
```

| Status | Meaning |
| --- | --- |
| 400 / 422 | Bad request or a domain-rule violation; `details` names the field |
| 401 | Missing, malformed or expired token |
| 403 | Authenticated but not permitted |
| 404 | Not found |
| 409 | Conflicts with existing state |
| 429 | Rate limited; `Retry-After` is set |
| 503 | Execution engine or AI tutor unavailable |

**Correlation ids.** Every response carries `X-Correlation-ID`. Send your own to
have it propagated. Quote it in bug reports.

**Pagination.** `?limit=` (1–200, default 50) and `?offset=`.

---

## Auth — `/api/auth`

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/register` | Create an account; returns profile + tokens (201) |
| POST | `/login` | Exchange credentials for tokens |
| POST | `/refresh` | Exchange a refresh token for a new pair |
| GET | `/me` | Current profile |
| PATCH | `/me` | Update display name, level, goal, preferences |
| POST | `/change-password` | Rotate the password |

```http
POST /api/auth/register
{"email": "ada@example.com", "password": "a-strong-password-1", "display_name": "Ada"}
```

Note: `/login` returns an identical error for an unknown email and a wrong
password, by design.

## Curriculum

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/courses` | Published learning paths |
| GET | `/courses/{slug}` | Course with its module/lesson tree |
| GET | `/lessons/{slug}` | Full lesson content, examples, exercises, progress |
| POST | `/lessons/{slug}/view` | Record a view; starts progress tracking |
| PUT | `/lessons/{slug}/scratch` | Autosave the lesson editor's files |
| POST | `/lessons/{slug}/time` | Report time on task (seconds) |
| POST | `/lessons/{slug}/complete` | Mark complete — **only succeeds once every attached exercise has a passing submission** |
| GET | `/concepts` | The concept catalogue; `?category=` to filter |
| GET | `/concepts/{slug}` | One concept and its prerequisites |
| GET | `/concepts/{slug}/lessons` | Lessons teaching a concept |

`GET /lessons/{slug}` returns a `sections` object with all ten required keys
(`what_is_it`, `why_it_exists`, `how_it_works`, `when_to_use`,
`when_not_to_use`, `common_mistakes`, `real_world`, `alternatives`,
`performance`, `security`). Content validation guarantees they are present.

## Exercises

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/exercises` | Browse the catalogue; `?concept=`, `?kind=`, `?level=` |
| GET | `/exercises/{slug}` | Everything needed to attempt it — never the hidden tests or the solution |
| POST | `/exercises/{slug}/submit` | Grade one attempt |
| GET | `/exercises/{slug}/submissions` | Attempt history, newest first |
| POST | `/exercises/{slug}/hints/{level}` | Unlock a hint rung |
| POST | `/exercises/{slug}/solution` | Reveal the reference solution |
| GET | `/exercises/{slug}/remediation` | Adaptive plan, or `null` if not stuck |
| GET | `/challenges` | Timed and open-ended challenges |

```http
POST /api/exercises/loops-fizzbuzz/submit
{"files": {"main.py": "def fizzbuzz(n): ..."}, "time_spent_seconds": 420}
```

```json
{
  "status": "partial",
  "score": 0.6,
  "checks": [{"name": "first five", "passed": true, "message": "Passed"}],
  "feedback": "3 of 5 tests passed. Read the first failure only…",
  "xp_awarded": 0,
  "mastery_deltas": [
    {"concept_slug": "loops", "previous": 0.31, "current": 0.44, "delta": 0.13, "band": "learning"}
  ],
  "newly_earned_achievements": []
}
```

**Hint ordering is enforced.** Requesting level 3 before level 2 returns 422 with
`details.next_available_level`.

**The solution is gated.** It unlocks after three attempts, after every hint has
been used, or once the exercise is passed. Otherwise 422, with the current
attempt and hint counts in `details`.

## Execution — `/api/execution`

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/run` | Run code in the sandbox |
| GET | `/health` | Which backend is live, and its limits |
| GET | `/snippets` | Saved Code Lab workspaces |
| PUT | `/snippets/{name}` | Save a workspace |
| DELETE | `/snippets/{name}` | Delete a workspace |

```http
POST /api/execution/run
{"files": {"main.py": "print(2+2)"}, "entrypoint": "main.py", "mode": "script"}
```

```json
{
  "ok": true, "exit_code": 0, "stdout": "4\n", "stderr": "",
  "timed_out": false, "duration_ms": 312,
  "stdout_truncated": false, "stderr_truncated": false,
  "error": null, "error_explanation": null
}
```

`mode` is `script` or `pytest`. `error_explanation` is a plain-language reading of
any traceback, produced by the same interpreter the grader uses.

Rejected before execution (422): absolute paths, `..`, non-allowlisted
extensions, more than `exec_max_files` files, total source above
`exec_max_source_bytes`, an entrypoint not in the file set.

## Progress and mastery

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/dashboard` | Everything the dashboard renders, in one call |
| GET | `/mastery` | Per-concept mastery, weak and strong areas |
| GET | `/mastery/readiness` | Which concepts are unlocked, and what blocks the rest |
| GET | `/recommendations` | Prioritised next steps |
| GET | `/progress/courses/{slug}` | Per-module completion and mastery |
| GET | `/achievements` | Every badge, earned or not |
| GET | `/certifications` | Progress on every track, with unmet requirements |
| POST | `/certifications/{level}/claim` | Award an earned certification |

Claiming an unearned certification returns 422 with
`details.unmet_requirements` — a list of exactly what is missing.

## Projects — `/api/projects`

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `` | The academy catalogue with your status on each |
| GET | `/{slug}` | Brief, rubric, milestones and your workspace |
| PUT | `/{slug}/workspace` | Autosave project files |
| POST | `/{slug}/run` | Run the project entrypoint |
| POST | `/{slug}/submit` | Acceptance tests + rubric evaluation + review |
| GET | `/{slug}/submissions` | Submission history |

`POST /{slug}/submit` returns per-criterion rubric scores and a markdown
engineering review. A project cannot pass on rubric points alone: the acceptance
tests must also be at least 80% green.

## AI tutor — `/api/ai`

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/status` | Backend, model, and today's remaining allowance |
| GET | `/conversations` | Recent threads |
| POST | `/conversations` | Start a thread; optionally pinned to a lesson/exercise |
| GET | `/conversations/{id}` | A thread with its messages |
| POST | `/conversations/{id}/messages` | Send a turn, receive the reply |
| DELETE | `/conversations/{id}` | Delete a thread |

Modes: `explain_code`, `explain_error`, `hint`, `socratic`, `review`,
`generate_exercise`, `generate_tests`, `mock_interview`, `freeform`.

The reply's `meta.withheld_solution` is `true` while the pinned exercise is
unsolved. The policy is rebuilt server-side from persisted state on every turn,
so it cannot be argued out of the model.

## Reference, search, review, interview

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/reference` | Index; `?module=`, `?kind=` |
| GET | `/reference/{key}` | One entry — signature, parameters, examples, pitfalls |
| GET | `/search?q=` | Global search; `?kinds=reference,lesson,concept,exercise,project` |
| POST | `/code-review` | Deterministic senior-engineer review of a file set |
| GET | `/interview/questions` | Question bank without answers; `?track=`, `?level=` |
| POST | `/interview/answer` | Grade one question and explain it |
| GET | `/analytics/me` | Your activity, accuracy and repeated mistakes |
| GET | `/analytics/platform` | Cohort analytics (author/admin only) |

`GET /search?q=How do I handle a timeout in requests?` returns ranked hits across
all five kinds; exact reference keys rank first, lessons are weighted slightly up.

## Meta

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness — the process is up |
| GET | `/ready` | Readiness — database and execution engine reachable |
| GET | `/openapi.json` | Machine-readable schema |

## Versioning

The prefix is `/api` and the schema version is the application version. Breaking
changes get a new prefix (`/api/v2`) with the previous one maintained for one
release cycle. Additive changes — new fields, new endpoints, new enum members —
are not breaking, so clients must ignore unknown fields.
