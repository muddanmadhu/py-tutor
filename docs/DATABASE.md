# Database Schema

PostgreSQL in production, SQLite for local development and tests. The schema is
portable: string UUID primary keys, `JSON` columns rather than `JSONB`-only
features, and timezone-aware timestamps everywhere.

## Entity relationships

```
                              ┌──────────┐
                              │  users   │
                              └────┬─────┘
        ┌──────────────┬───────────┼────────────┬──────────────┬─────────────┐
        │              │           │            │              │             │
┌───────▼──────┐ ┌─────▼──────┐ ┌──▼─────────┐ ┌▼───────────┐ ┌▼──────────┐ ┌▼────────────┐
│ submissions  │ │concept_    │ │lesson_     │ │project_    │ │ai_convers-│ │certifications│
│              │ │mastery     │ │progress    │ │submissions │ │ations     │ │              │
└───────┬──────┘ └─────┬──────┘ └──┬─────────┘ └┬───────────┘ └┬──────────┘ └─────────────┘
        │              │           │            │              │
        │        ┌─────▼──────┐    │      ┌─────▼──────┐  ┌────▼────────┐
        │        │  concepts  │    │      │  projects  │  │ ai_messages │
        │        └─────┬──────┘    │      └────────────┘  └─────────────┘
        │              │           │
        │      ┌───────▼─────────┐ │
        │      │ concept_        │ │
        │      │ prerequisites   │ │   (self-referential DAG)
        │      └─────────────────┘ │
        │              │           │
        │      ┌───────▼─────────┐ │
        │      │ lesson_concepts │ │   (many-to-many)
        │      └───────┬─────────┘ │
        │              │           │
┌───────▼──────┐ ┌─────▼──────┐   │
│  exercises   │◄┤  lessons   │◄──┘
│              │ └─────┬──────┘
└───────┬──────┘       │
        │        ┌─────▼──────┐      ┌──────────┐
   ┌────▼────┐   │  modules   │◄─────┤ courses  │
   │  hints  │   └────────────┘      └──────────┘
   └─────────┘
```

Standalone: `reference_entries`, `quiz_questions`, `achievements`,
`user_achievements`, `execution_runs`, `saved_snippets`, `hint_reveals`,
`project_workspaces`, `learning_events`.

## Tables

### Identity

**`users`** — learners, authors and admins.
Key columns: `email` (unique, indexed), `password_hash`, `role`,
`declared_level`, `xp`, `streak_days`, `longest_streak_days`, `last_active_on`,
`total_coding_seconds`, `preferences` (JSON), `active_course_slug`.

### Curriculum

**`courses`** → **`modules`** → **`lessons`**, each ordered by `position`.

**`lessons`** carries the authored content: `body` (markdown), `sections` (the
ten required keys), `starter_code`, `examples`, `visualizations`,
`reference_keys`, `xp_reward`. `slug` is globally unique so lessons can be linked
without knowing their module.

**`concepts`** — the unit of mastery. `difficulty` and `weight` feed the mastery
model: harder concepts move a score more slowly, heavier ones dominate the
roll-up. `common_misconceptions` holds the targeted explanations the remediation
engine serves.

**`lesson_concepts`** — many-to-many. A concept is taught by one lesson and
reinforced by several.

**`concept_prerequisites`** — a self-referential DAG. `tests/test_content.py`
asserts it is acyclic; a cycle would deadlock the readiness calculation.

### Assessment

**`exercises`** — the gradeable unit.

| Column | Purpose |
| --- | --- |
| `starter_files` | Pre-loaded into the editor |
| `hidden_files` | Merged at grade time, never served to the client |
| `solution_files` | Served only by the gated solution endpoint |
| `grader` + `grader_config` | The grader contract, as data |
| `concept_slugs` | Which concepts this assesses — drives mastery updates |
| `misconception_rules` | Output patterns → misconception ids |

Keeping the grader as *data* rather than code per exercise is what makes
authoring hundreds of exercises tractable.

**`hints`** — one row per rung, unique on `(exercise_id, level)`.

**`submissions`** — every attempt, never overwritten. The mastery engine, the
analytics layer and the adaptive engine all reason over the *sequence*.

**`hint_reveals`** — which rungs a learner unlocked. Persisted so mastery can be
discounted, so a hint cannot be re-locked to dodge the penalty, and so analytics
can show which exercises need better teaching upstream. `source='solution'`
records a give-up.

**`execution_runs`** — ad-hoc sandbox runs. Separate from submissions: running
code to explore is the core activity and a signal in its own right, but it is not
an assessment.

### Progress

**`concept_mastery`** — unique on `(user_id, concept_id)`.

| Column | Meaning |
| --- | --- |
| `score` | 0–1 estimate; **not** a completion percentage |
| `confidence` | How much evidence backs the score |
| `attempts`, `correct_attempts`, `first_try_correct` | Raw counters |
| `hints_used`, `solutions_viewed` | Assistance consumed |
| `misconception_counts` | JSON tally, drives remediation |
| `last_practiced_at` | Input to the retention decay applied on read |
| `mastered_at` | Set when thresholds are met; cleared when they stop being met |

**`lesson_progress`** — status, view count, time on task, and `scratch_files` so
a learner's editor state survives navigation.

**`learning_events`** — append-only analytics. Deliberately schema-light;
aggregates are computed on read.

### Projects

**`projects`** — brief, rubric, milestones, starter files and acceptance tests.
`guidance` implements the fade-out from fully guided to independent.

**`project_workspaces`** — unique on `(user_id, project_id)`; the autosaved IDE
state.

**`project_submissions`** — acceptance-test tally, per-criterion rubric scores,
the markdown review and the verdict.

### Gamification

**`achievements`** with data-driven `criteria`; **`user_achievements`** as the
join; **`certifications`** storing a snapshot of the evidence that justified each
award, so a certificate can always be explained after the fact.

### AI

**`ai_conversations`** — `context` pins a thread to a lesson or exercise;
`hint_level_reached` is server-side state the tutor policy reads.
**`ai_messages`** — one row per turn, with model and token usage in `meta`.

### Reference

**`reference_entries`** — keyed on the natural lookup handle (`list.append`,
`requests.get`). Stored in the database rather than served as static files so it
participates in search and can be cross-linked from lessons.

## Indexes

Every index exists for a query that runs on a page load:

| Index | Serves |
| --- | --- |
| `users.email` (unique) | login |
| `lessons.slug` (unique) | lesson page |
| `exercises.slug` (unique) | exercise page |
| `(course_id, position)` on modules | course tree |
| `(module_id, position)` on lessons | course tree |
| `(user_id, exercise_id)` on submissions | attempt count, best score |
| `(user_id, created_at)` on submissions | recent activity |
| `(user_id, concept_id)` on concept_mastery (unique) | mastery upsert |
| `(user_id, score)` on concept_mastery | weak-area query |
| `(user_id, status)` on lesson_progress | course progress |
| `(user_id, occurred_at)` on learning_events | activity series |
| `(kind, occurred_at)` on learning_events | cohort analytics |
| `reference_entries.key` (unique) | reference lookup |

## Conventions

**Primary keys** are 32-character UUID4 hex strings. Portable across SQLite and
PostgreSQL, and assignable before flush, which simplifies building object graphs
in one transaction.

**Timestamps** are `DateTime(timezone=True)` with database-side defaults. Naive
datetimes never enter the codebase; `app.db.base.utcnow` is the only clock.

**Cascades** are declared both in the ORM (`cascade="all, delete-orphan"`) and in
the database (`ondelete="CASCADE"`, with `passive_deletes=True`). Deleting a user
removes everything of theirs in one statement rather than one round-trip per row.

**Constraint naming** follows a fixed convention (`app/db/base.py`), so Alembic
generates stable, reversible migrations. Unnamed constraints are the usual cause
of a migration that cannot be downgraded.

**Enums are strings, not native database enums.** Adding a curriculum kind is a
code change rather than a migration, which matters for content that grows
continuously.

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

The baseline revision (`0001_initial`) builds the schema from the ORM metadata
rather than from a transcribed list of `create_table` calls, so revision one
cannot drift from the models. Every subsequent revision is a normal autogenerated
diff. CI runs `upgrade → downgrade base → upgrade` on every pull request.

## Growth

At the scale where this stops being comfortable, in the order it will bite:

1. **`learning_events`** grows fastest. Partition by month, and archive beyond a
   retention window.
2. **`submissions`** keeps every attempt including its files. Move `files` to
   object storage once the table is large; keep the metadata.
3. **Cohort analytics** (`hardest_exercises`, `hardest_concepts`) currently scan.
   Move to a nightly materialised view.
4. **Search** moves from application scoring to PostgreSQL `tsvector` +
   `pg_trgm`; the interface is one method on `SearchService`.
