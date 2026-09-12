# Curriculum Roadmap — Scaling to ~600 Hours

Status: **proposed, not yet built.** This is the architecture document for the
expansion from the current 59 h seed curriculum to ~600 h. Nothing in
`app/content/` has changed yet. See [CURRICULUM.md](CURRICULUM.md) for the
authoring model this plan follows — the roadmap adds content, not mechanism.

---

## 1. Where the current 60 hours actually comes from

`CourseSpec.estimated_hours` is a hand-written literal
([`app/content/__init__.py`](../backend/app/content/__init__.py)), but it is an
honest one — it matches the content when you add the three sources up:

| Source | Count | Time |
| --- | --- | --- |
| Lessons | 13 | 367 min = 6.1 h |
| Exercises | 18 | 249 min = 4.2 h |
| Projects | 4 | 49.0 h |
| **True total** | | **59.3 h** (declared 60) |

Two things follow. Lesson prose is only **10%** of the programme — the hours are
overwhelmingly in exercises and projects, which is what the README means by
"learners spend most of their time writing, running, breaking and fixing
Python". And the declared figure is not derived, so it can silently drift out of
step with the content. §7 proposes fixing that.

## 2. Target composition

Scaled project-heavy, preserving the existing shape rather than turning PyForge
into a tutorial site:

| Source | Now | Target | Count |
| --- | --- | --- | --- |
| Lessons | 6.1 h | **71 h** | 13 → 122 (+109) |
| Exercises | 4.2 h | **91 h** | 18 → 345 (+327) |
| Projects | 49.0 h | **436 h** | 4 → 28 (+24) |
| **Total** | **59.3 h** | **598.5 h** | |

Projects carry **73%** of the hours. The plan lands at 598.5 h, not exactly 600
— I would rather show the real arithmetic than pad a project's estimate by 1.5 h
to hit a round number.

## 3. Module map

Modules 1–3 exist and are unchanged. Modules 4–19 are new. Exercise counts
assume 3 per lesson at ~16 min, matching the current average of 14 min.

| # | Module | Level | Lessons | Lesson h | Ex | Ex h |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `foundations` *(exists)* | beginner | 4 | 1.5 | 7 | 1.4 |
| 2 | `core-python` *(exists)* | intermediate | 4 | 1.9 | 6 | 1.5 |
| 3 | `professional-python` *(exists)* | professional | 5 | 2.8 | 5 | 1.3 |
| 4 | `data-structures-and-algorithms` | intermediate | 8 | 4.7 | 24 | 6.4 |
| 5 | `text-and-regex` | intermediate | 5 | 2.8 | 15 | 4.0 |
| 6 | `iterators-and-generators` | intermediate | 6 | 3.3 | 18 | 4.8 |
| 7 | `functional-python` | advanced | 6 | 3.5 | 18 | 4.8 |
| 8 | `oop-in-depth` | advanced | 8 | 4.8 | 24 | 6.4 |
| 9 | `typing-and-contracts` | advanced | 6 | 3.3 | 18 | 4.8 |
| 10 | `concurrency-and-async` | advanced | 8 | 5.0 | 24 | 6.4 |
| 11 | `databases-and-persistence` | professional | 7 | 4.3 | 21 | 5.6 |
| 12 | `web-services` | professional | 8 | 5.0 | 24 | 6.4 |
| 13 | `data-engineering` | professional | 7 | 4.3 | 21 | 5.6 |
| 14 | `testing-in-depth` | professional | 7 | 4.2 | 21 | 5.6 |
| 15 | `packaging-and-tooling` | professional | 6 | 3.3 | 18 | 4.8 |
| 16 | `performance-and-internals` | engineering | 7 | 4.3 | 21 | 5.6 |
| 17 | `security-engineering` | engineering | 6 | 3.7 | 18 | 4.8 |
| 18 | `operations-and-deployment` | engineering | 7 | 4.3 | 21 | 5.6 |
| 19 | `architecture-and-design` | engineering | 7 | 4.3 | 21 | 5.6 |
| | **Total** | | **122** | **71.1** | **345** | **91.4** |

This covers every gap [CURRICULUM.md §Scaling](CURRICULUM.md) names — regex,
generators, decorators, async, databases, web frameworks, Docker, internals —
plus typing, packaging, security and architecture.

## 4. Project academy ladder

Guidance fades as level rises, per the table in
[CURRICULUM.md §Writing a project](CURRICULUM.md).

| Project | Level | Guidance | h |
| --- | --- | --- | --- |
| `calculator-cli` *(exists)* | beginner | fully_guided | 2 |
| `text-adventure-engine` | beginner | fully_guided | 4 |
| `unit-converter-toolkit` | beginner | fully_guided | 3 |
| `flashcard-trainer` | beginner | fully_guided | 5 |
| `expense-tracker-cli` *(exists)* | intermediate | partially_guided | 5 |
| `log-analyzer` | intermediate | partially_guided | 8 |
| `static-site-generator` | intermediate | partially_guided | 10 |
| `csv-report-engine` | intermediate | partially_guided | 9 |
| `regex-log-parser` | intermediate | partially_guided | 8 |
| `inventory-manager` | intermediate | partially_guided | 10 |
| `async-web-crawler` | advanced | partially_guided | 16 |
| `task-queue-engine` | advanced | partially_guided | 18 |
| `cli-framework` | advanced | partially_guided | 14 |
| `orm-from-scratch` | advanced | requirements_only | 20 |
| `plugin-architecture` | advanced | requirements_only | 16 |
| `caching-layer` | advanced | requirements_only | 12 |
| `file-processing-platform` *(exists)* | professional | requirements_only | 12 |
| `rest-api-service` | professional | requirements_only | 24 |
| `auth-rbac-service` | professional | requirements_only | 20 |
| `etl-pipeline` | professional | requirements_only | 22 |
| `realtime-metrics-service` | professional | requirements_only | 20 |
| `multi-tenant-saas-backend` | professional | requirements_only | 28 |
| `search-service` | professional | requirements_only | 18 |
| `distributed-job-scheduler` | engineering | independent | 30 |
| `observability-platform` | engineering | independent | 26 |
| `payment-reconciliation-system` | engineering | independent | 24 |
| `data-platform-migration` | engineering | independent | 22 |
| `enterprise-automation-service` *(exists, capstone)* | engineering | independent | 30 |
| | | **Total** | **436** |

Every new project needs `acceptance_tests` written against the **observable
contract** and a weighted `rubric` — `validate()` rejects a project with no
rubric, and `app/services/projects.py` only interprets the eleven documented
rubric keys.

## 5. Concepts and certification — the one load-bearing risk

The mastery model needs concepts behind this content: roughly **150 new
concepts** (43 → ~193) across new categories — `algorithms`, `regex`,
`iterators`, `functional`, `typing`, `concurrency`, `web`, `data-engineering`,
`packaging`, `performance`, `security`, `operations`, `architecture`.

**This is the part that can quietly break something already working.**
`app/services/certification.py` gates each certification on named categories
reaching an average mastery threshold. Adding concepts to an *existing*
category changes what an existing certificate means — dropping 20 new
`advanced` concepts into the pool moves the average a learner needs for the
Advanced certification, potentially revoking one someone has already earned.

The plan therefore puts new concepts in **new categories** by default. Existing
categories (`fundamentals`, `control-flow`, `functions`, `collections`,
`errors`, `oop`, `advanced`, `files`, `apis`, `automation`, `testing`,
`debugging`, `databases`) are touched only where a deliberate decision is
recorded. The new tracks need their own certifications — **that is a decision
for you, not a default I should pick.**

## 6. Tranche plan

Each tranche ends green on `pytest tests/test_content.py` and a rebuilt static
bundle, so the site is never in a broken intermediate state.

| # | Tranche | Lands |
| --- | --- | --- |
| 0 | Concept scaffolding | ~150 concepts, new categories, prerequisite graph |
| 1 | Modules 4–7 | 25 lessons, 75 exercises |
| 2 | Modules 8–10 | 22 lessons, 66 exercises |
| 3 | Modules 11–13 | 22 lessons, 66 exercises |
| 4 | Modules 14–16 | 20 lessons, 60 exercises |
| 5 | Modules 17–19 | 20 lessons, 60 exercises |
| 6 | Projects, beginner → advanced | 14 projects, 153 h |
| 7 | Projects, professional → engineering | 10 projects, 234 h |
| 8 | Reference, quizzes, achievements | ~200 reference entries, interview bank |
| 9 | Certifications + hours figure | new tracks, derived `estimated_hours` |

Tranche 0 must land first: `validate()` rejects any lesson referencing an
unknown concept, so lessons cannot be authored before their concepts exist.

## 7. Make the hours figure derived, not declared

Once this lands, `estimated_hours=60` becomes `600` — a literal that is right
only until the next content change. Since the three inputs are all in the
content tree, the number should be computed from them and the literal deleted.
That removes the whole class of drift we hit when auditing the current 60.

Recommended alongside tranche 9, as a small, separately reviewable change.

## 8. Honest scope note

This is a large authoring job: ~109 lessons, ~327 exercises with four-rung hint
ladders and hidden pytest files, ~24 projects with acceptance tests and rubrics,
~150 concepts, ~200 reference entries. Existing lessons run 12–17 KB of authored
Python each; the expansion is on the order of **1.5–2 MB** of new content.

It is not a single sitting. The tranche structure exists so that each step is
reviewable and the curriculum is coherent and shippable at every stage, rather
than 80% of a shape nobody signed off on.

For calibration: 600 h exceeds a typical university Python sequence (150–300 h)
and is comparable to a full bootcamp.
