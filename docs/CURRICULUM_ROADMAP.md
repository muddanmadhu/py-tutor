# Curriculum Roadmap — 100 Hours

Target revised 600 h → 300 h → **100 h** (2026-09-12), project-heavy. The target
is **met**: `estimated_hours` derives to exactly 100 from the content in the tree.

See [CURRICULUM.md](CURRICULUM.md) for the authoring model. This document records
what the 100 hours consists of, how it is counted, and what a future expansion
would add.

---

## 1. How the hours are counted

`CourseSpec.estimated_hours` is **derived**, not declared
([`app/content/__init__.py`](../backend/app/content/__init__.py)), so it cannot
drift from the content:

```
lesson estimated_minutes + exercise estimated_minutes
                         ────────────────────────────  + project estimated_hours
                                     60
```

Lesson time and exercise time are separate fields — a lesson's
`estimated_minutes` covers the teaching material only.

## 2. Composition

| Source | Start | **Now** | Count |
| --- | --- | --- | --- |
| Lessons | 6.1 h | **9.1 h** | 13 → 19 |
| Exercises | 4.2 h | **8.3 h** | 18 → 36 |
| Projects | 49.0 h | **83.0 h** | 4 → 11 |
| **Total** | **59.3 h** | **100 h** | |

Projects carry **83%** of the programme. That is the project-heavy shape asked
for, and it matches the README's claim that learners spend most of their time
writing, running, breaking and fixing Python rather than reading.

The Python Reference grew 16 → **49** entries. Reference material is lookup, not
timed study, so it carries no estimated hours and does not appear above.

## 3. Modules

| # | Module | Level | Lessons | Ex |
| --- | --- | --- | --- | --- |
| 1 | `foundations` | beginner | 4 | 7 |
| 2 | `data-structures-and-algorithms` | intermediate | 6 | 18 |
| 3 | `core-python` | intermediate | 4 | 6 |
| 4 | `professional-python` | professional | 5 | 5 |
| | **Total** | | **19** | **36** |

## 4. The project ladder

Eleven projects, guidance fading monotonically, every prerequisite ahead of its
dependent. The seven added for the 100 h target are production-like: the kind of
task handed to an engineer in their first year, stated as a business requirement.

| Project | Level | Guidance | h |
| --- | --- | --- | --- |
| `calculator-cli` | beginner | fully_guided | 2 |
| `expense-tracker-cli` | intermediate | partially_guided | 5 |
| `log-analyzer` **new** | intermediate | partially_guided | 4 |
| `csv-report-engine` **new** | intermediate | partially_guided | 4 |
| `api-client-sdk` **new** | intermediate | partially_guided | 4 |
| `invoice-reconciliation` **new** | professional | requirements_only | 5 |
| `etl-pipeline` **new** | professional | requirements_only | 5 |
| `inventory-sync-service` **new** | professional | requirements_only | 6 |
| `file-processing-platform` | professional | requirements_only | 12 |
| `incident-report-pipeline` **new** | engineering | independent | 6 |
| `enterprise-automation-service` *(capstone)* | engineering | independent | 30 |
| | | **Total** | **83** |

**94 acceptance tests** across the seven new projects, written against the
observable contract rather than an assumed design.

### The constraint that shaped them

The static build runs learner code under Pyodide: no network, no database. So a
project "about" HTTP is graded on the logic *around* HTTP — retry classification,
backoff, `Retry-After`, pagination — with the transport injected by the test.
`api-client-sdk` and `etl-pipeline` both take an injected collaborator (`send`,
`load`) and `inventory-sync-service` takes `apply`. That is also how this code
should be tested in production, so the constraint improved the design rather than
limiting it.

## 5. The Python Reference — why it grew

An audit found **18 of 19 lessons cited `reference_keys` with no matching
entry**. `validate()` does not check those keys, so the "look this up" links were
dead across nearly the whole curriculum, including the original content.

All 28 missing keys now exist, plus the APIs the data-structures module teaches
(`collections.deque`, `heapq`, `bisect`, `Counter`, `defaultdict`) which a
learner reaches for immediately afterwards. Every lesson reference link resolves;
a test asserting that would be a worthwhile addition.

## 6. Concepts and certification

48 concepts. The five added with module 2 sit in a **new `algorithms` category**,
because `app/services/certification.py` gates certificates on the average mastery
of named categories — adding to an existing category retroactively changes what
an already-issued certificate meant. Nothing requires `algorithms` yet, so no
certificate changed meaning.

The new tracks could have their own certifications. That is a product decision,
not a default worth picking silently.

## 7. What "done" means, and what it caught

Every tranche is verified beyond `validate()`:

- each exercise's reference solution **passes** its hidden tests (15/15)
- each exercise's starter files **fail** them — this caught
  `complexity-fix-quadratic` shipping **pre-solved**, because its timing
  threshold was loose enough for the quadratic starter to pass
- every `Example` output reproduced by executing it — 24 lesson examples and
  **106 reference examples**, which caught one wrong claimed output in `bisect`
- acceptance tests must not error on collection, and must not pass vacuously:
  two did, and were removed or strengthened

## 8. If this grows again

The next increments, in value order:

1. **A test that every `reference_keys` entry resolves.** The gap above existed
   because nothing checked. Cheap, and prevents recurrence.
2. **Module 5, `text-and-regex`** — 6 lessons, 18 exercises, ~5 h. The `regex`
   concept exists and is taught nowhere.
3. **Generators and decorators** — the only other unreferenced concepts.
4. More projects. At 83 h of 100, projects are where hours accumulate fastest:
   one professional build is worth roughly a whole lesson module.
