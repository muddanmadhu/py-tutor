"""Achievements and the interview question bank.

Achievement criteria are interpreted by :mod:`app.services.gamification`. Every
one is tied to demonstrated work — passing exercises, mastering concepts,
completing projects — never to time spent or pages viewed.
"""

from __future__ import annotations

from app.content.schema import AchievementSpec, QuizSpec
from app.models.enums import SkillLevel

ACHIEVEMENTS: tuple[AchievementSpec, ...] = (
    AchievementSpec(
        slug="first-steps",
        name="First Steps",
        description="Passed your first exercise.",
        icon="footprints",
        tier="bronze",
        xp_reward=25,
        criteria={"type": "exercises_passed", "count": 1},
    ),
    AchievementSpec(
        slug="getting-going",
        name="Getting Going",
        description="Passed 10 exercises.",
        icon="zap",
        tier="bronze",
        xp_reward=60,
        criteria={"type": "exercises_passed", "count": 10},
    ),
    AchievementSpec(
        slug="practitioner",
        name="Practitioner",
        description="Passed 25 exercises.",
        icon="dumbbell",
        tier="silver",
        xp_reward=150,
        criteria={"type": "exercises_passed", "count": 25},
    ),
    AchievementSpec(
        slug="unaided",
        name="No Hints Needed",
        description="Passed 5 exercises first time, with no hints and no solution.",
        icon="target",
        tier="silver",
        xp_reward=200,
        criteria={"type": "unaided_passes", "count": 5},
    ),
    AchievementSpec(
        slug="bug-hunter",
        name="Bug Hunter",
        description="Fixed 3 debugging challenges.",
        icon="bug",
        tier="silver",
        xp_reward=150,
        criteria={"type": "debug_fixes", "count": 3},
    ),
    AchievementSpec(
        slug="concept-collector",
        name="Concept Collector",
        description="Reached mastery on 5 concepts.",
        icon="brain",
        tier="silver",
        xp_reward=200,
        criteria={"type": "concepts_mastered", "count": 5},
    ),
    AchievementSpec(
        slug="deep-mastery",
        name="Deep Mastery",
        description="Reached mastery on 20 concepts.",
        icon="award",
        tier="gold",
        xp_reward=500,
        criteria={"type": "concepts_mastered", "count": 20},
    ),
    AchievementSpec(
        slug="builder",
        name="Builder",
        description="Completed your first project.",
        icon="hammer",
        tier="silver",
        xp_reward=250,
        criteria={"type": "projects_completed", "count": 1},
    ),
    AchievementSpec(
        slug="shipped",
        name="Shipped It",
        description="Completed 3 projects.",
        icon="rocket",
        tier="gold",
        xp_reward=600,
        criteria={"type": "projects_completed", "count": 3},
    ),
    AchievementSpec(
        slug="consistent",
        name="Consistent",
        description="A 7-day learning streak.",
        icon="flame",
        tier="bronze",
        xp_reward=100,
        criteria={"type": "streak_days", "count": 7},
    ),
    AchievementSpec(
        slug="relentless",
        name="Relentless",
        description="A 30-day learning streak.",
        icon="flame",
        tier="gold",
        xp_reward=500,
        criteria={"type": "streak_days", "count": 30},
    ),
    AchievementSpec(
        slug="scholar",
        name="Scholar",
        description="Completed 10 lessons.",
        icon="book-open",
        tier="bronze",
        xp_reward=100,
        criteria={"type": "lessons_completed", "count": 10},
    ),
)


QUIZ_BANK: tuple[QuizSpec, ...] = (
    QuizSpec(
        slug="iq-mutable-default",
        question="What does this print, and why is it a classic interview question?",
        code_snippet="def f(x, acc=[]):\n    acc.append(x)\n    return acc\n\n"
        "print(f(1))\nprint(f(2))",
        options=(
            "[1] then [2] — each call gets a fresh list",
            "[1] then [1, 2] — the default list is created once and shared between calls",
            "It raises a TypeError",
            "[1] then [2] with a DeprecationWarning",
        ),
        correct_index=1,
        explanation="Default arguments are evaluated once, when the `def` statement executes. "
        "Every call that omits `acc` therefore shares the same list object. The fix is the "
        "sentinel pattern: `acc=None`, then `if acc is None: acc = []`.",
        category="functions",
        level=SkillLevel.INTERMEDIATE,
        tracks=("python-developer", "backend", "sdet"),
        concepts=("functions", "mutability"),
    ),
    QuizSpec(
        slug="iq-is-vs-equals",
        question="When is `is` the correct operator to use instead of `==`?",
        options=(
            "Whenever comparing values, because it is faster",
            "Only when comparing against None, True, False or a specific sentinel object — "
            "`is` tests object identity, not equality of value",
            "When comparing strings, because they are interned",
            "When comparing integers below 257",
        ),
        correct_index=1,
        explanation="`is` asks whether two names refer to the *same object*. CPython caches "
        "small integers and interns some strings, so `is` can appear to work on values — that "
        "is an implementation detail, not a guarantee, and relying on it produces bugs that "
        "surface only with larger values.",
        category="fundamentals",
        level=SkillLevel.BEGINNER,
        tracks=("python-developer", "sdet", "automation"),
        concepts=("operators", "variables"),
    ),
    QuizSpec(
        slug="iq-gil",
        question="What does the GIL prevent, and what does it not?",
        options=(
            "It prevents all concurrency in Python",
            "It prevents two threads executing Python bytecode simultaneously, so it limits "
            "CPU-bound threading — but I/O releases it, so threads still help I/O-bound work, "
            "and multiprocessing sidesteps it entirely",
            "It prevents memory corruption in multiprocessing",
            "It prevents asyncio from running coroutines in parallel",
        ),
        correct_index=1,
        explanation="The Global Interpreter Lock serialises execution of Python bytecode "
        "within one process. Blocking I/O releases it, so threads are effective for network "
        "and disk work. For CPU-bound parallelism use `multiprocessing` or push the work into "
        "a C extension that releases the GIL.",
        category="advanced",
        level=SkillLevel.ADVANCED,
        tracks=("backend", "python-developer"),
        concepts=("concurrency",),
    ),
    QuizSpec(
        slug="iq-list-vs-tuple",
        question="Beyond mutability, what is the practical difference between a list and a tuple?",
        options=(
            "Tuples are always faster for every operation",
            "Tuples are hashable when their contents are, so they can be dict keys and set "
            "members; they also signal that the collection is a fixed record rather than a "
            "varying sequence",
            "Lists cannot contain mixed types",
            "Tuples cannot be iterated",
        ),
        correct_index=1,
        explanation="Hashability is the functional difference: `{(1, 2): 'point'}` works, "
        "`{[1, 2]: ...}` raises TypeError. The design signal matters too — a tuple says 'this "
        "has a fixed shape and each position means something'.",
        category="collections",
        level=SkillLevel.INTERMEDIATE,
        tracks=("python-developer", "sdet"),
        concepts=("tuples", "lists", "mutability"),
    ),
    QuizSpec(
        slug="iq-generator-memory",
        question="Why use a generator instead of a list?",
        options=(
            "Generators are always faster",
            "A generator produces values lazily, so memory stays constant regardless of the "
            "sequence length, and work stops as soon as the consumer stops — at the cost of "
            "being single-pass and not indexable",
            "Generators can be reused indefinitely",
            "Generators support random access",
        ),
        correct_index=1,
        explanation="`sum(x*x for x in range(10**8))` uses constant memory; the list "
        "comprehension version needs gigabytes. The trade-off is that a generator is "
        "exhausted after one pass and has no `len()` or indexing.",
        category="advanced",
        level=SkillLevel.ADVANCED,
        tracks=("backend", "python-developer"),
        concepts=("generators", "performance"),
    ),
    QuizSpec(
        slug="iq-shallow-deep-copy",
        question="`b = a.copy()` on a list of lists. You then run `b[0].append(1)`. What "
        "happens to `a`?",
        options=(
            "Nothing — copy() is a full copy",
            "`a[0]` also gains the element: copy() duplicates the outer list but the inner "
            "lists are shared references",
            "A TypeError is raised",
            "`a` becomes None",
        ),
        correct_index=1,
        explanation="`copy()` is shallow: the new list holds references to the same inner "
        "objects. Use `copy.deepcopy(a)` when the nesting matters. This bug hides completely "
        "when the contents are immutable.",
        category="collections",
        level=SkillLevel.INTERMEDIATE,
        tracks=("python-developer", "sdet", "backend"),
        concepts=("mutability", "lists"),
    ),
    QuizSpec(
        slug="iq-retry-strategy",
        question="Your API client gets a 404. Should it retry?",
        options=(
            "Yes, with exponential backoff",
            "No — 4xx means the request itself is wrong, and it will be wrong the second "
            "time too. Retry 429 and 5xx; fail fast on other 4xx",
            "Yes, but only once",
            "Only if the response body is empty",
        ),
        correct_index=1,
        explanation="Retrying a permanent client error wastes time and rate-limit budget "
        "while producing the same failure. Retry the transient classes — 429 (honouring "
        "Retry-After) and 5xx — with exponential backoff and jitter.",
        category="apis",
        level=SkillLevel.PROFESSIONAL,
        tracks=("backend", "automation", "sdet"),
        concepts=("api-clients", "http-basics"),
    ),
    QuizSpec(
        slug="iq-test-quality",
        question="A test suite reports 100% coverage. What does that tell you?",
        options=(
            "The code is correct",
            "Every line executed during the run — but nothing about whether the behaviour "
            "was asserted, whether edge cases were covered, or whether the assertions are "
            "meaningful",
            "There are no bugs in the tested code",
            "Every branch has been tested",
        ),
        correct_index=1,
        explanation="Coverage measures execution, not verification. A test that calls every "
        "function and asserts nothing reaches 100%. Even branch coverage says nothing about "
        "input values. Use coverage to find code nobody tested at all, not as a quality "
        "target.",
        category="testing",
        level=SkillLevel.INTERMEDIATE,
        tracks=("sdet", "test-architect", "backend"),
        concepts=("unit-testing", "test-design"),
    ),
    QuizSpec(
        slug="iq-sql-injection",
        question="Which of these is safe from SQL injection?",
        code_snippet='A: cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n'
        'B: cursor.execute("SELECT * FROM users WHERE id = " + str(user_id))\n'
        'C: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))\n'
        'D: cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)',
        options=(
            "A — f-strings escape their inputs",
            "C — the value is passed as a query parameter, so the driver sends it separately "
            "from the SQL text and it can never be interpreted as code",
            "B — str() sanitises the value",
            "All of them, if user_id came from an integer field",
        ),
        correct_index=1,
        explanation="Only parameterisation is safe. A, B and D all build SQL text from a "
        "value. `str(user_id)` does not sanitise anything, and 'it came from an integer "
        "field' is an assumption that fails the moment the input path changes. "
        "Parameterisation also lets the database cache the query plan.",
        category="databases",
        level=SkillLevel.PROFESSIONAL,
        tracks=("backend", "automation", "sdet"),
        concepts=("databases", "security-basics"),
    ),
    QuizSpec(
        slug="iq-decorator-purpose",
        question="What problem do decorators solve?",
        options=(
            "They make functions run faster",
            "They add behaviour around a function — logging, timing, caching, "
            "authentication — without editing the function or its call sites, keeping the "
            "cross-cutting concern in one place",
            "They enforce type checking at runtime",
            "They convert functions into classes",
        ),
        correct_index=1,
        explanation="A decorator is a function that takes a function and returns a wrapped "
        "one. `@lru_cache`, `@app.route`, `@pytest.fixture` and `@property` are all the same "
        "mechanism. Use `functools.wraps` in your own so the wrapper keeps the original's "
        "name and docstring.",
        category="functions",
        level=SkillLevel.ADVANCED,
        tracks=("python-developer", "backend"),
        concepts=("decorators", "closures"),
    ),
    QuizSpec(
        slug="iq-context-manager",
        question="Why is `with open(path) as f:` better than `f = open(path)`?",
        options=(
            "It is shorter to type",
            "The file is closed when the block exits, including when an exception is raised — "
            "which also guarantees buffered writes are flushed",
            "It opens the file faster",
            "It automatically detects the encoding",
        ),
        correct_index=1,
        explanation="`with` calls `__exit__` on the way out of the block whatever happens. "
        "Without it, an exception between open and close leaks the handle and can silently "
        "lose buffered writes.",
        category="files",
        level=SkillLevel.INTERMEDIATE,
        tracks=("python-developer", "automation", "sdet"),
        concepts=("file-io", "exceptions"),
    ),
    QuizSpec(
        slug="iq-idempotency",
        question="Why does an unattended batch job need to be idempotent?",
        options=(
            "To make it run faster",
            "Because it will eventually crash part-way through, and someone will re-run it — "
            "if a re-run duplicates or corrupts work, recovery requires manual reconciliation "
            "instead of just running it again",
            "Because the scheduler requires it",
            "To reduce memory usage",
        ),
        correct_index=1,
        explanation="Idempotency is what makes 'just run it again' a valid recovery "
        "procedure. Without it, every partial failure becomes a manual investigation. The "
        "usual mechanisms are upserts keyed on a natural id, a processed-ledger, and marking "
        "work complete only *after* the output is durable.",
        category="automation",
        level=SkillLevel.PROFESSIONAL,
        tracks=("automation", "backend", "test-architect"),
        concepts=("automation-design",),
    ),
)
