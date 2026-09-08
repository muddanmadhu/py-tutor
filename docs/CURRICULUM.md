# Curriculum Architecture

## The model

```
Course ──► Module ──► Lesson ──► Exercise ──► Hint (×4)
                        │
                        └──► Concept ◄──── Concept (prerequisites, a DAG)
                                 ▲
                                 └──── ConceptMastery (per learner)
```

**Concepts are first-class, not nested inside lessons.** "Closures" is taught in
one lesson, reinforced in three others and assessed in a project. Mastery is
tracked per concept, so concepts are linked to lessons and exercises
many-to-many. This is the single most important structural decision in the
content model: it is what lets mastery mean "can use this idea" rather than
"reached this page".

## Content is typed Python

`app/content/` holds dataclasses, not YAML. Three reasons:

1. **It type-checks.** A misspelled field is a `mypy` error.
2. **It can share constants.** Concept slugs are *referenced*, so a typo is a
   `ContentError` rather than an orphaned mastery record.
3. **It fails at import.** `validate()` runs when the module is imported, so a
   malformed lesson is a startup failure with a precise message rather than a
   mystery in production.

```
app/content/
├── schema.py            the dataclasses + validate()
├── concepts.py          the concept graph
├── lessons/
│   ├── foundations.py   Module 01–02
│   ├── core.py          Module 03–04
│   └── professional.py  Module 05–06
├── projects.py          the project academy
├── reference_entries.py the Python reference
├── achievements.py      badges + the interview bank
└── __init__.py          assembles the course and validates everything
```

## What validation enforces

`validate()` refuses to let content load if:

* two lessons or two exercises share a slug
* a lesson is missing any of the ten required sections
* a lesson or exercise references a concept that does not exist
* a concept's prerequisite does not exist
* a pytest-graded exercise has no hidden test files
* a stdout-graded exercise has no expected output
* a static-assert exercise has no assertions
* a quiz's answer key is out of range
* a non-quiz exercise has no hint ladder
* a project has no rubric

`tests/test_content.py` adds more: four-rung ladders, reference solutions with
explanations, an acyclic prerequisite graph, no orphan concepts, and certification
requirements that point at real categories and projects.

## Writing a lesson

```python
from app.content.schema import Example, ExerciseSpec, HintSpec, LessonSpec
from app.models.enums import ExerciseKind, GraderKind, SkillLevel

MY_LESSON = LessonSpec(
    slug="decorators",                      # globally unique, URL-safe
    title="Decorators: Wrapping Behaviour",
    summary="One sentence a learner sees in the course tree.",
    level=SkillLevel.ADVANCED,
    estimated_minutes=30,
    concepts=("decorators", "closures"),    # must exist in concepts.py
    reference_keys=("functools.wraps",),
    body="""\
## Markdown teaching content

Code fences, tables and ASCII diagrams all render. Write the *why* before the
*how* — a learner who knows why a feature exists can derive the syntax.
""",
    sections={
        # All ten are mandatory. See below.
        "what_is_it": "...",
        "why_it_exists": "...",
        "how_it_works": "...",
        "when_to_use": "...",
        "when_not_to_use": "...",
        "common_mistakes": "...",
        "real_world": "...",
        "alternatives": "...",
        "performance": "...",
        "security": "...",
    },
    starter_code="# runnable from the first click\n",
    examples=(
        Example(
            title="The mechanism, minimally",
            code="...",
            output="...",
            explanation="What to notice, and why.",
        ),
    ),
    exercises=(...),
)
```

Then add it to a `ModuleSpec` and run `make seed`.

### The ten sections

Every lesson answers all of them. This is spec §49 turned into a schema
constraint, so "we'll add the security note later" is not possible.

| Key | The question |
| --- | --- |
| `what_is_it` | What is it? |
| `why_it_exists` | Why does it exist? |
| `how_it_works` | How does it work? |
| `when_to_use` | When should I use it? |
| `when_not_to_use` | When should I NOT use it? |
| `common_mistakes` | What are common mistakes? |
| `real_world` | How is it used in real projects? |
| `alternatives` | What are the alternatives? |
| `performance` | What are the performance implications? |
| `security` | What are the security implications? |

`when_not_to_use` is the one authors skip and the one learners need most. A
feature you cannot say *no* to is a feature you do not understand.

## Writing an exercise

```python
ExerciseSpec(
    slug="decorators-timing",
    title="Write a timing decorator",
    prompt="Markdown. State the contract precisely: names, types, edge cases.",
    kind=ExerciseKind.CODE,
    difficulty=0.7,                      # 0–1; feeds the mastery model
    estimated_minutes=15,
    starter_files={"main.py": "def timed(func):\n    ...\n"},
    hidden_files={"test_timing.py": "..."},   # never served to the client
    solution_files={"main.py": "..."},
    solution_explanation="Why this solution, and what to take away.",
    grader=GraderKind.PYTEST,
    concepts=("decorators",),            # drives the mastery update
    hints=(
        HintSpec("Conceptual clue: which idea applies, and why here."),
        HintSpec("Direction: the shape of the approach, in words, no code."),
        HintSpec("Specific area: which line or expression is wrong."),
        HintSpec("Partial solution: structure or pseudocode, key step left out."),
    ),
    misconception_rules=(
        {"pattern": "test_preserves_name", "misconception": "missing-functools-wraps"},
    ),
)
```

### The graders

| Grader | Use for | Configuration |
| --- | --- | --- |
| `PYTEST` | Anything with a function contract | `hidden_files` containing `test_*.py` |
| `STDOUT_MATCH` | Beginner output exercises | `{"expected_stdout": "...", "ignore_case": false}` |
| `STATIC_ASSERT` | "Use a comprehension", "add type hints" | `{"target_file", "assertions": [...]}` |
| `MULTIPLE_CHOICE` | Concept checks | `{"options", "correct_index", "explanation", "misconception_per_option"}` |

`STATIC_ASSERT` uses the AST, so a construct mentioned in a comment or a string
never counts as a use. Available assertion kinds: `defines_function`,
`defines_class`, `uses_construct`, `forbids_construct`, `calls_function`,
`imports_module`, `max_lines`, `has_docstring`, `has_type_hints`.

### The hint ladder

Exactly four rungs, escalating:

```
1  Conceptual clue    — which idea applies, and why it applies here
2  Direction          — the shape of the approach, in words, no code
3  Specific area      — which line or expression is wrong, and what is wrong
4  Partial solution   — structure or pseudocode with the key step left to them
```

The full solution is never a hint. It lives on the exercise and unlocks
separately, after three attempts or once every hint is used.

### Misconception rules

`{"pattern": <regex>, "misconception": <slug>}` matched against grader output.
A matched slug is tallied on `concept_mastery.misconception_counts`, surfaces on
the dashboard as a repeated mistake, and drives the remediation ladder. Prefer
matching a *test name* over matching an error message: test names are stable.

## Writing a project

Projects implement the guidance fade-out from spec §50:

| `guidance` | Learner gets |
| --- | --- |
| `FULLY_GUIDED` | Every milestone spelled out, starter files, a suggested structure |
| `PARTIALLY_GUIDED` | Module boundaries given, logic theirs |
| `REQUIREMENTS_ONLY` | A business requirement and constraints; no structure |
| `INDEPENDENT` | A requirement document and a rubric, nothing else |

Every project needs `acceptance_tests` (run in the sandbox) and a weighted
`rubric`. Rubric keys are interpreted by `app/services/projects.py`; the
recognised ones are `correctness`, `architecture`, `testing`, `error_handling`,
`security`, `performance`, `readability`, `maintainability`, `logging`,
`documentation`, `deployment`. An unknown key falls back to the overall
code-quality score.

Write acceptance tests against the **observable contract**, not an assumed
design — for a requirements-only project the design is the learner's to choose.
`file-processing-platform` shows the pattern: `pytest.importorskip` with a message
telling the learner what interface to expose.

## Writing a reference entry

Each entry answers what a learner needs at the moment they look something up:
signature, parameters, return value, a runnable example, the mistake people make,
performance and security notes, and what to use instead. `keywords` adds search
terms that are not in the title — this is how "how do I handle a timeout in
requests?" finds `requests.get`.

## Adding a concept

```python
ConceptSpec(
    slug="metaclasses",
    name="Metaclasses",
    description="Classes that create classes.",
    category="advanced",              # feeds certification requirements
    level=SkillLevel.ADVANCED,
    difficulty=0.9,                   # harder concepts move mastery more slowly
    weight=0.8,                       # how much it counts in the roll-up
    prerequisites=("classes", "decorators"),
    misconceptions=(
        {"slug": "metaclass-overuse",
         "explanation": "Targeted explanation the remediation engine serves."},
    ),
)
```

`category` is load-bearing: `app/services/certification.py` requires named
categories to reach a threshold, so adding a concept to a category changes what
a certificate means. Do it deliberately.

## Scaling the curriculum

The seed content covers the thirteen required topics plus four projects. To add
the rest of the specification's syllabus — regex, generators, decorators, async,
databases, web frameworks, Docker, internals — the pattern is unchanged:

1. Add concepts to `concepts.py`, with honest prerequisites.
2. Add a lesson module under `lessons/`, and register it in a `ModuleSpec`.
3. Add exercises with four-rung ladders and hidden tests.
4. Add reference entries for the APIs the lesson uses.
5. Add interview questions to `achievements.py`.
6. Run `pytest tests/test_content.py` — it will tell you what is missing.
7. `make seed`.

No code changes anywhere else. That is the point of the design.

## Content review checklist

- [ ] All ten sections present and substantive — especially `when_not_to_use`
- [ ] `body` teaches the *why* before the *how*
- [ ] Every example is runnable, and its stated output is correct
- [ ] Starter code runs and produces something on the first click
- [ ] Exercise prompts state the contract precisely (names, types, edge cases)
- [ ] Hidden tests cover the happy path, boundaries and at least one failure mode
- [ ] Hidden test failure messages teach, not just report
- [ ] Four hint rungs, escalating, none of which is the solution
- [ ] The reference solution is idiomatic and its explanation says *why*
- [ ] Concepts listed are the ones actually assessed
- [ ] `difficulty` is honest — it changes how mastery moves
