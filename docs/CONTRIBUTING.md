# Contributing

## Before you start

```bash
cp .env.example .env
make venv          # backend virtualenv + dev dependencies
cd frontend && npm install
make up            # or run the services locally, see docs/SETUP.md
make seed
make check         # confirm a clean baseline before you change anything
```

Read `docs/ARCHITECTURE.md` first, and skim `app/services/mastery.py` — it is the
part of the system whose design decisions everything else follows from.

## Workflow

1. Branch from `main`: `feature/…`, `fix/…`, `content/…` or `docs/…`.
2. Make the change, with tests.
3. `make check` — the same commands CI runs.
4. Open a pull request describing **what** changed and **why**.

## Commit messages

Conventional Commits:

```
feat(mastery): decay confidence when a concept goes unpractised
fix(execution): kill the process group, not just the leader
content(lessons): add the regular expressions lesson
docs(security): document the Docker socket trade-off
test(grading): cover the pytest collection-error path
refactor(api): move exercise assembly into a service
```

Body: what changed, why, and anything a reviewer would otherwise have to ask.

## Pull request checklist

- [ ] `make check` passes
- [ ] New behaviour has tests; a bug fix has a test that failed before the fix
- [ ] Type hints on everything new; `mypy --strict` is clean
- [ ] Docstrings explain *why*, not just what
- [ ] No secrets, tokens or personal data in code, tests, fixtures or logs
- [ ] Documentation updated if behaviour, configuration or the API changed
- [ ] For content: `pytest tests/test_content.py` passes and the
      `docs/CURRICULUM.md` review checklist is satisfied
- [ ] For anything touching execution or auth: the `docs/SECURITY.md` checklist

## What gets pushed back on in review

* **Business logic in a router.** Routers adapt HTTP to a service call.
* **A service that opens its own session.** Transaction boundaries live at the
  edge.
* **`raise HTTPException` from a service.** Use `app.core.errors`.
* **Reading `os.environ` outside `core/config.py`.**
* **A bare `except:` or `except Exception: pass`.** The review engine flags these
  in learner code; we hold ourselves to it too.
* **A test asserting on a private attribute.** It will break on the next
  refactor and protects nothing.
* **A new sandbox capability without a test proving the new boundary.**
* **A lesson missing `when_not_to_use`.** The validator will catch it, but it
  signals the lesson was written from the syntax rather than from the idea.
* **`# noqa` with no rule and no reason.**

## Contributing content

Content is as reviewable as code, and it is where the platform's value actually
lives. `docs/CURRICULUM.md` has the full authoring guide; the essentials:

* Teach the *why* before the *how*.
* Every claim about Python must be true. If you are not certain, run it.
* Every example's stated output must be the real output.
* Four hint rungs, escalating, none of which is the answer.
* Hidden tests should cover boundaries and at least one failure mode, and their
  assertion messages should teach.
* British or American spelling is fine; be consistent within a lesson.
* Write for a specific reader: someone competent who has not met this idea yet.
  Not a beginner to be talked down to, and not an expert to be impressed.

## Reporting bugs

Include:

* the correlation id from the response (`X-Correlation-ID`) — it is one grep away
  from the full server-side story
* what you expected and what happened
* the exercise or lesson slug, if relevant
* the output of `GET /api/execution/health` for sandbox problems

## Security issues

Do not open a public issue. See `docs/SECURITY.md` for the reporting process.

## Code of conduct

Be straightforward and kind. Review the code, not the person. Assume the author
had a reason and ask what it was. Disagreement is fine and useful; contempt is
not.
