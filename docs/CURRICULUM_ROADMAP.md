# Curriculum Roadmap — Scaling to ~300 Hours

Target revised from 600 h to **~300 h** (2026-09-12), project-heavy. See
[CURRICULUM.md](CURRICULUM.md) for the authoring model this follows — the roadmap
adds content, not mechanism.

**Tranche 1 of 9 has landed.** Module 4 is built and validated; the rest is
planned. Progress is in §6.

---

## 1. How the hours are counted

`CourseSpec.estimated_hours` is now **derived** from the content rather than
declared ([`app/content/__init__.py`](../backend/app/content/__init__.py)), so it
cannot drift. It is the sum of three sources, and lesson time and exercise time
are separate fields:

```
lesson estimated_minutes + exercise estimated_minutes
                         ────────────────────────────  + project estimated_hours
                                     60
```

At the start of this work that came to 59.3 h (declared as a literal 60, which
happened to be right). The literal is gone.

## 2. Target composition

| Source | Start | **Now** | Target | Count at target |
| --- | --- | --- | --- | --- |
| Lessons | 6.1 h | **9.1 h** | 30.1 h | 13 → 61 (+48) |
| Exercises | 4.2 h | **8.3 h** | 42.5 h | 18 → 162 (+144) |
| Projects | 49.0 h | 49.0 h | 227.3 h | 4 → 16 (+12) |
| **Total** | **59.3 h** | **66.5 h** | **299.9 h** | |

Projects carry **76%** of the hours at target, which is what "project-heavy"
means here: lesson prose stays a tenth of the programme and the time goes where
learners write code.

## 3. Module map

Modules 1–3 existed. Module 4 is built. Modules 5–11 are planned at 6 lessons
and 18 exercises each — the shape module 4 established.

| # | Module | Level | Lessons | Ex | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | `foundations` | beginner | 4 | 7 | existing |
| 2 | `core-python` | intermediate | 4 | 6 | existing |
| 3 | `professional-python` | professional | 5 | 5 | existing |
| 4 | `data-structures-and-algorithms` | intermediate | 6 | 18 | **built** |
| 5 | `text-and-regex` | intermediate | 6 | 18 | planned |
| 6 | `iterators-and-generators` | intermediate | 6 | 18 | planned |
| 7 | `functional-python` | advanced | 6 | 18 | planned |
| 8 | `typing-and-contracts` | advanced | 6 | 18 | planned |
| 9 | `concurrency-and-async` | advanced | 6 | 18 | planned |
| 10 | `databases-and-persistence` | professional | 6 | 18 | planned |
| 11 | `web-services-and-operations` | professional | 6 | 18 | planned |
| | **Total** | | **61** | **162** | |

This covers the gaps [CURRICULUM.md §Scaling](CURRICULUM.md) names — regex,
generators, decorators, async, databases, web frameworks, Docker — plus typing.
Dropped relative to the 600 h plan: separate modules for OOP depth, testing
depth, packaging, performance internals, security and architecture. Those
subjects are not absent; they stay where they already are in module 3 and in the
project rubrics.

## 4. Project academy ladder

Guidance fades as level rises, per
[CURRICULUM.md §Writing a project](CURRICULUM.md).

| Project | Level | Guidance | h |
| --- | --- | --- | --- |
| `calculator-cli` *(exists)* | beginner | fully_guided | 2 |
| `text-adventure-engine` | beginner | fully_guided | 4 |
| `flashcard-trainer` | beginner | fully_guided | 5 |
| `expense-tracker-cli` *(exists)* | intermediate | partially_guided | 5 |
| `log-analyzer` | intermediate | partially_guided | 8 |
| `static-site-generator` | intermediate | partially_guided | 10 |
| `csv-report-engine` | intermediate | partially_guided | 9 |
| `async-web-crawler` | advanced | partially_guided | 16 |
| `cli-framework` | advanced | partially_guided | 14 |
| `orm-from-scratch` | advanced | requirements_only | 20 |
| `file-processing-platform` *(exists)* | professional | requirements_only | 12 |
| `rest-api-service` | professional | requirements_only | 24 |
| `auth-rbac-service` | professional | requirements_only | 20 |
| `etl-pipeline` | professional | requirements_only | 22 |
| `observability-platform` | engineering | independent | 26 |
| `enterprise-automation-service` *(exists, capstone)* | engineering | independent | 30 |
| | | **Total** | **227** |

Every new project needs `acceptance_tests` written against the **observable
contract** and a weighted `rubric` — `validate()` rejects a project with no
rubric, and `app/services/projects.py` interprets only the eleven documented
rubric keys.

## 5. Concepts and certification — the load-bearing risk

Concept count is 43 → **48**. Module 4 added five in a **new `algorithms`
category**: `sorting`, `complexity`, `searching`, `stacks-queues`, `heaps`.

`app/services/certification.py` gates each certification on named concept
categories reaching an average mastery threshold. Adding concepts to an
*existing* category changes what an existing certificate means — 20 new
`advanced` concepts would move the average a learner needs for the Advanced
certification, potentially revoking one already earned. So new concepts go in
**new categories** by default, and module 4 followed that rule.

The new tracks will eventually want their own certifications. **That remains a
decision for you, not a default to pick.** Nothing requires `algorithms` yet, so
no existing certificate changed meaning.

An earlier draft of this plan assumed many needed concepts already existed as
unused stubs. That was wrong: of 43 concepts only three (`generators`,
`closures`, `decorators`) are unreferenced. Concepts must be authored per module.

## 6. Tranche plan and progress

Each tranche ends green on `pytest tests/test_content.py` and a rebuilt bundle,
so the site is never in a broken intermediate state.

| # | Tranche | Lands | Status |
| --- | --- | --- | --- |
| 1 | Module 4 + `algorithms` concepts + derived hours | 6 lessons, 18 exercises, 5 concepts | **done** |
| 2 | Module 5 `text-and-regex` | 6 lessons, 18 exercises, concepts | next |
| 3 | Module 6 `iterators-and-generators` | 6 lessons, 18 exercises | |
| 4 | Module 7 `functional-python` | 6 lessons, 18 exercises | |
| 5 | Module 8 `typing-and-contracts` | 6 lessons, 18 exercises | |
| 6 | Module 9 `concurrency-and-async` | 6 lessons, 18 exercises | |
| 7 | Modules 10–11 databases + web services | 12 lessons, 36 exercises | |
| 8 | Projects, beginner → advanced | 6 projects, 86 h | |
| 9 | Projects, professional → engineering | 6 projects, 92 h + reference entries | |

Concepts land with their module rather than all up front, because `validate()`
rejects a lesson referencing a concept that does not exist but does not mind
concepts arriving late.

## 7. What "done" means for a lesson

Module 4 set the bar, and it is mechanically checkable. For every exercise:

- the reference solution **passes** its own hidden tests
- the starter files **fail** them — otherwise the exercise ships pre-solved
- four escalating hint rungs, none of which is the solution
- hidden-test failure messages teach rather than just report

And for every lesson, all ten required sections, plus every `Example`'s stated
output verified by executing it. Both checks are worth re-running per tranche;
the pre-solved case is not hypothetical — it caught `complexity-fix-quadratic`,
whose timing threshold was loose enough for the quadratic starter to pass.

## 8. Scope note

Remaining after tranche 1: **42 lessons, 126 exercises, 12 projects** and their
concepts and reference entries. Existing lesson modules run 46–87 KB of authored
Python each; module 4 is ~60 KB for six lessons, so the remainder is on the order
of **400–500 KB** of new content.

Not one sitting. The tranche structure exists so each step is reviewable and the
curriculum is coherent and shippable throughout.
