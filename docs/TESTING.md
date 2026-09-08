# Testing Strategy

## The pyramid, and what lives at each level

```
        ╱  E2E  ╲              e2e/            ~30 tests, minutes
      ╱───────────╲            Playwright against a running stack
    ╱  Integration  ╲          tests/test_api.py, test_docker_isolation.py
  ╱───────────────────╲        real HTTP, real database, real containers
╱       Unit tests      ╲      tests/test_mastery.py, test_grading.py,
                              test_code_review.py, test_services.py,
                              test_execution.py, test_content.py
```

The unit and integration suites run with no infrastructure at all — SQLite plus
the subprocess executor — and finish in seconds. That is deliberate: a suite
people run on every save protects more than a thorough one they skip.

## Running

```bash
cd backend
pytest                              # everything except docker-marked tests
pytest tests/test_mastery.py -v
pytest -k hint
pytest -m docker -v                 # needs the daemon + runner image
pytest --cov=app --cov-report=html

cd ../e2e && npm test               # needs a running stack
```

## What each suite is responsible for

| File | Covers |
| --- | --- |
| `test_execution.py` | Job validation (path escape, size, count, entrypoint), timeouts, output truncation, multi-file runs, pytest mode, workspace isolation between runs, rate limiting |
| `test_docker_isolation.py` | The security claims: no network, no DNS, read-only rootfs, non-root UID, memory cap, PID cap, container cleanup |
| `test_mastery.py` | Evidence weighting, difficulty adjustment, retention decay, bands, mastery being *lost*, misconception tallies, overall roll-up |
| `test_grading.py` | All four graders, output normalisation, diff generation, traceback interpretation, authored misconception rules, AST-based structural checks |
| `test_code_review.py` | Every finding the review engine can produce, and the absence of false positives on clean code |
| `test_services.py` | Password hashing, token type confusion, auth error parity, streaks, XP levels, adaptive recommendations, remediation, certification gating, search ranking, the AI hint policy |
| `test_content.py` | The curriculum itself: required sections, hint ladders, solutions, acyclic prerequisites, no orphan concepts, rubric validity, answer keys |
| `test_api.py` | The HTTP contract end to end, including the error envelope and every authorisation boundary |
| `e2e/definition-of-done.spec.ts` | The twenty Definition-of-Done steps, in one browser session |
| `e2e/accessibility.spec.ts` | Skip link, keyboard navigation, labels, ARIA values, theme persistence, responsive reflow |

## Content is tested like code

`test_content.py` is unusual and worth explaining. A lesson with an unreachable
solution or a test suite that contradicts its own brief wastes a learner's time
just as surely as a bug does, so the curriculum is asserted against:

* every lesson answers all ten required questions (spec §49)
* every lesson has a substantial body, worked examples, starter code and at least
  one exercise
* every non-quiz exercise has a **four**-rung hint ladder, a reference solution
  and an explanation of that solution
* every pytest-graded exercise ships a hidden suite whose filename starts
  `test_`
* the concept prerequisite graph is acyclic
* no concept is orphaned — everything is taught, assessed, or used by a project
  or interview question
* every certification's required categories and projects actually exist
* every quiz answer key is in range and every explanation is substantive
* no achievement rewards attendance rather than work (spec §42)

This is what makes "hundreds more lessons" safe: the tests fail on a malformed
one before it reaches a learner.

## Notable test techniques

**The tutor's hint policy is tested as a string contract.** `build_system_prompt`
is a pure function, so `test_services.py` asserts that a practising context
contains "Do NOT write the solution" and that the reference solution never
appears in the prompt at all — a property that would be very hard to test by
observing model output.

**The infinite-loop test is a real infinite loop.** `test_execution.py` submits
`while True: pass` and asserts the sandbox stops it. Simulating that would test
the simulation.

**The test-writing exercise grades the learner's tests by running them against a
deliberately broken implementation.** If the learner's suite passes against
broken code, it is not asserting enough, and the meta-test fails them. See
`app/content/lessons/professional.py`, exercise `testing-find-the-bug`.

**Mastery decay is tested by moving the clock backwards in the database**, not by
sleeping.

## Fixtures

| Fixture | Provides |
| --- | --- |
| `session` | A file-backed SQLite database with a fresh schema |
| `seeded_session` | The same, with the full curriculum loaded |
| `client` / `seeded_client` | `TestClient` sharing the test's session |
| `user` / `auth_headers` | A registered learner and their bearer header |
| `executor` | The configured execution backend |

File-backed rather than `:memory:` because the API and the test share a
connection pool; in-memory would give each connection its own empty schema.

## Coverage

Target 80% on `app/` excluding `app/content/` (prose) and `alembic/`. Coverage is
used to find code nobody tested at all, not as a score to maximise — a test that
calls every function and asserts nothing reaches 100%.

Deliberately not covered: the Anthropic client's network path (mocked at the
boundary), Alembic scripts (exercised by the CI migration job instead).

## CI

Four jobs, in `.github/workflows/ci.yml`:

| Job | What it proves |
| --- | --- |
| `backend` | Lint, `mypy --strict`, the full suite with coverage, migrations apply *and reverse*, the seed content loads into PostgreSQL |
| `sandbox` | The isolation claims, against a real daemon |
| `frontend` | ESLint, `tsc --noEmit`, a production build |
| `e2e` | The Definition of Done, in a browser, against the composed stack |

A red build blocks the merge. The migration job runs
`upgrade → downgrade base → upgrade`, so a one-way migration fails.

## Writing a good test here

* **Name the behaviour, not the function.** `test_solution_is_gated_behind_effort`
  tells you what broke; `test_solution_2` does not.
* **Assert on observable behaviour.** A test that reads `_balance` breaks on
  every refactor and protects nothing.
* **Cover the edges.** Empty, one, the boundary, one past it, negative, zero,
  None, duplicates, unicode, and the largest realistic size.
* **One behaviour per test.** When it fails you should not have to read the body
  to know what is wrong.
* **A bug fix starts with a failing test.** It proves the fix and prevents the
  regression.
* **Mock at the boundary only.** A test where everything is mocked tests the
  mocks.
