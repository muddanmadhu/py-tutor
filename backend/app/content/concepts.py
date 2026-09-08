"""The concept graph.

Concepts are the unit of mastery. Categories map onto certification
requirements (see :mod:`app.services.certification`), so adding a concept to a
category changes what a certificate means — do it deliberately.
"""

from __future__ import annotations

from app.content.schema import ConceptSpec
from app.models.enums import SkillLevel

CONCEPTS: tuple[ConceptSpec, ...] = (
    # -- fundamentals -------------------------------------------------------
    ConceptSpec(
        slug="variables",
        name="Variables and assignment",
        description="Names bound to objects; rebinding, and why Python names are labels "
        "rather than boxes.",
        category="fundamentals",
        level=SkillLevel.BEGINNER,
        difficulty=0.15,
        weight=1.2,
        misconceptions=(
            {
                "slug": "aliasing",
                "explanation": "Assignment never copies. `b = a` makes a second label for "
                "the *same* object, so mutating through one name is visible through the "
                "other. Only immutable objects hide this, because they cannot be mutated.",
            },
        ),
    ),
    ConceptSpec(
        slug="data-types",
        name="Core data types",
        description="int, float, bool, str, None — what each represents and how they convert.",
        category="fundamentals",
        level=SkillLevel.BEGINNER,
        difficulty=0.2,
        weight=1.2,
        prerequisites=("variables",),
        misconceptions=(
            {
                "slug": "type-mismatch",
                "explanation": "`input()` always returns a str, even when the user types "
                "digits. `'5' + 1` is a TypeError; convert first with `int(...)`.",
            },
            {
                "slug": "value-conversion",
                "explanation": "`int('12.5')` raises ValueError: int() parses integers, not "
                "decimal text. Use `float('12.5')`, then `int(...)` if you want truncation.",
            },
        ),
    ),
    ConceptSpec(
        slug="operators",
        name="Operators",
        description="Arithmetic, comparison, logical, membership, identity and bitwise "
        "operators, and their precedence.",
        category="fundamentals",
        level=SkillLevel.BEGINNER,
        difficulty=0.25,
        prerequisites=("data-types",),
        misconceptions=(
            {
                "slug": "identity-vs-equality",
                "explanation": "`is` asks 'the same object?'; `==` asks 'the same value?'. "
                "Small ints and short strings are cached, so `is` sometimes appears to work "
                "on values — it is still wrong.",
            },
        ),
    ),
    ConceptSpec(
        slug="io-basics",
        name="Input and output",
        description="print() and input(): how a program talks to a person.",
        category="fundamentals",
        level=SkillLevel.BEGINNER,
        difficulty=0.15,
        prerequisites=("data-types",),
    ),
    # -- control flow -------------------------------------------------------
    ConceptSpec(
        slug="conditionals",
        name="Conditional execution",
        description="if / elif / else, truthiness and conditional expressions.",
        category="control-flow",
        level=SkillLevel.BEGINNER,
        difficulty=0.3,
        weight=1.3,
        prerequisites=("operators",),
        misconceptions=(
            {
                "slug": "chained-comparison",
                "explanation": "`if x == 1 or 2:` is always true — `2` is truthy on its own. "
                "Write `if x in (1, 2):` or `if x == 1 or x == 2:`.",
            },
        ),
    ),
    ConceptSpec(
        slug="loops",
        name="Loops",
        description="for and while, range(), enumerate(), zip(), break, continue.",
        category="control-flow",
        level=SkillLevel.BEGINNER,
        difficulty=0.35,
        weight=1.4,
        prerequisites=("conditionals",),
        misconceptions=(
            {
                "slug": "infinite-loop",
                "explanation": "A `while` loop needs something inside its body to change the "
                "condition. If the counter is never incremented, the condition stays true "
                "for ever.",
            },
            {
                "slug": "off-by-one",
                "explanation": "`range(n)` produces 0 to n-1: n values, not n+1. Indexing a "
                "list of length n with n is always an IndexError.",
            },
            {
                "slug": "mutate-while-iterating",
                "explanation": "Removing items from a list while looping over it makes the "
                "loop skip elements. Build a new list, or iterate over a copy.",
            },
        ),
    ),
    # -- collections --------------------------------------------------------
    ConceptSpec(
        slug="strings",
        name="Strings and text processing",
        description="Indexing, slicing, f-strings and the string method vocabulary.",
        category="collections",
        level=SkillLevel.BEGINNER,
        difficulty=0.3,
        weight=1.3,
        prerequisites=("data-types",),
        misconceptions=(
            {
                "slug": "string-immutability",
                "explanation": "Strings cannot be changed in place. `s.upper()` returns a new "
                "string; it does not modify `s`. Assign the result.",
            },
        ),
    ),
    ConceptSpec(
        slug="lists",
        name="Lists",
        description="Ordered, mutable sequences: indexing, slicing, and the mutation methods.",
        category="collections",
        level=SkillLevel.BEGINNER,
        difficulty=0.35,
        weight=1.4,
        prerequisites=("loops",),
        misconceptions=(
            {
                "slug": "aliasing",
                "explanation": "`b = a` for a list gives two names for one list. Use "
                "`a.copy()` or `a[:]` when you want an independent list.",
            },
            {
                "slug": "sort-returns-none",
                "explanation": "`list.sort()` sorts in place and returns None. "
                "`sorted(list)` returns a new sorted list. Assigning the result of `.sort()` "
                "gives you None.",
            },
        ),
    ),
    ConceptSpec(
        slug="tuples",
        name="Tuples",
        description="Immutable sequences, unpacking, and when immutability is the point.",
        category="collections",
        level=SkillLevel.BEGINNER,
        difficulty=0.3,
        prerequisites=("lists",),
    ),
    ConceptSpec(
        slug="dictionaries",
        name="Dictionaries",
        description="Key–value mappings: lookup, insertion, iteration and the .get() idiom.",
        category="collections",
        level=SkillLevel.BEGINNER,
        difficulty=0.4,
        weight=1.4,
        prerequisites=("lists",),
        misconceptions=(
            {
                "slug": "missing-key",
                "explanation": "`d[key]` raises KeyError when the key is absent. Use "
                "`d.get(key)` for None, `d.get(key, default)` for a fallback, or `in` to test.",
            },
        ),
    ),
    ConceptSpec(
        slug="sets",
        name="Sets",
        description="Unordered collections of unique, hashable values, and set algebra.",
        category="collections",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.4,
        prerequisites=("dictionaries",),
    ),
    ConceptSpec(
        slug="comprehensions",
        name="Comprehensions",
        description="Building lists, dicts and sets declaratively.",
        category="collections",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.5,
        prerequisites=("lists", "loops"),
    ),
    ConceptSpec(
        slug="mutability",
        name="Mutability and copying",
        description="Mutable vs immutable, shallow vs deep copy, and hashability.",
        category="collections",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.6,
        weight=1.2,
        prerequisites=("lists", "dictionaries"),
        misconceptions=(
            {
                "slug": "shallow-copy",
                "explanation": "`list.copy()` copies the outer list only. Nested lists are "
                "still shared. Use `copy.deepcopy` when the nesting matters.",
            },
        ),
    ),
    # -- functions ----------------------------------------------------------
    ConceptSpec(
        slug="functions",
        name="Functions",
        description="Defining, calling, parameters, arguments and return values.",
        category="functions",
        level=SkillLevel.BEGINNER,
        difficulty=0.4,
        weight=1.6,
        prerequisites=("conditionals",),
        misconceptions=(
            {
                "slug": "missing-return",
                "explanation": "A function without a `return` gives back None. Printing "
                "inside a function is not the same as returning: you cannot use a print.",
            },
            {
                "slug": "mutable-default",
                "explanation": "`def f(items=[])` evaluates that list once, at definition "
                "time, and reuses it on every call. Use `items=None` and create it inside.",
            },
        ),
    ),
    ConceptSpec(
        slug="scope",
        name="Scope and the LEGB rule",
        description="Local, Enclosing, Global, Built-in name resolution; global and nonlocal.",
        category="functions",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.6,
        prerequisites=("functions",),
    ),
    ConceptSpec(
        slug="args-kwargs",
        name="*args and **kwargs",
        description="Variadic positional and keyword parameters, and argument unpacking.",
        category="functions",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.55,
        prerequisites=("functions",),
    ),
    ConceptSpec(
        slug="closures",
        name="Closures",
        description="Functions that capture variables from an enclosing scope.",
        category="functions",
        level=SkillLevel.ADVANCED,
        difficulty=0.75,
        prerequisites=("scope",),
        misconceptions=(
            {
                "slug": "late-binding-closure",
                "explanation": "A closure captures the *variable*, not its value at creation "
                "time. Functions made in a loop all see the final value. Bind it with a "
                "default argument: `lambda x, i=i: ...`.",
            },
        ),
    ),
    ConceptSpec(
        slug="decorators",
        name="Decorators",
        description="Wrapping a function to add behaviour without editing it.",
        category="functions",
        level=SkillLevel.ADVANCED,
        difficulty=0.8,
        weight=1.2,
        prerequisites=("closures", "args-kwargs"),
    ),
    ConceptSpec(
        slug="generators",
        name="Generators and iterators",
        description="Lazy sequences with yield; the iterator protocol.",
        category="advanced",
        level=SkillLevel.ADVANCED,
        difficulty=0.75,
        prerequisites=("functions", "loops"),
    ),
    ConceptSpec(
        slug="type-hints",
        name="Type hints",
        description="Annotating code so tools — and readers — can check intent.",
        category="advanced",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.5,
        prerequisites=("functions",),
    ),
    # -- errors -------------------------------------------------------------
    ConceptSpec(
        slug="exceptions",
        name="Exceptions",
        description="try/except/else/finally, raising, and the exception hierarchy.",
        category="errors",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.5,
        weight=1.5,
        prerequisites=("functions",),
        misconceptions=(
            {
                "slug": "broad-except",
                "explanation": "`except Exception:` hides bugs as well as the failure you "
                "expected. Catch the specific class you can actually recover from.",
            },
            {
                "slug": "swallowed-exception",
                "explanation": "`except ...: pass` turns a crash into wrong behaviour with "
                "no evidence. At minimum, log it.",
            },
        ),
    ),
    ConceptSpec(
        slug="custom-exceptions",
        name="Custom exceptions",
        description="Domain-specific exception classes and exception chaining.",
        category="errors",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.6,
        prerequisites=("exceptions", "classes"),
    ),
    ConceptSpec(
        slug="debugging",
        name="Debugging",
        description="Reading tracebacks, forming hypotheses, bisecting, and using a debugger.",
        category="debugging",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.6,
        weight=1.5,
        prerequisites=("exceptions",),
    ),
    # -- OOP ----------------------------------------------------------------
    ConceptSpec(
        slug="classes",
        name="Classes and objects",
        description="Defining types: __init__, attributes, instance methods.",
        category="oop",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.55,
        weight=1.5,
        prerequisites=("functions",),
        misconceptions=(
            {
                "slug": "forgot-self",
                "explanation": "Instance methods take `self` first. Without it, Python "
                "passes the instance into your first named parameter and the errors get "
                "confusing fast.",
            },
            {
                "slug": "class-attribute-shared",
                "explanation": "An attribute assigned in the class body is shared by every "
                "instance. Per-instance state belongs in `__init__`.",
            },
        ),
    ),
    ConceptSpec(
        slug="inheritance",
        name="Inheritance and polymorphism",
        description="Reusing and specialising behaviour; when composition is better.",
        category="oop",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.65,
        prerequisites=("classes",),
    ),
    ConceptSpec(
        slug="dunder-methods",
        name="Magic methods",
        description="__str__, __repr__, __eq__, __len__, __iter__, __enter__ and friends.",
        category="oop",
        level=SkillLevel.ADVANCED,
        difficulty=0.7,
        prerequisites=("classes",),
    ),
    ConceptSpec(
        slug="dataclasses",
        name="Dataclasses",
        description="Declarative value types without boilerplate.",
        category="oop",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.5,
        prerequisites=("classes", "type-hints"),
    ),
    # -- files & data -------------------------------------------------------
    ConceptSpec(
        slug="file-io",
        name="File input/output",
        description="Reading and writing files safely with context managers and pathlib.",
        category="files",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.5,
        weight=1.4,
        prerequisites=("exceptions",),
        misconceptions=(
            {
                "slug": "unclosed-file",
                "explanation": "Without `with`, a file stays open until the garbage "
                "collector gets to it — and on an exception, buffered writes can be lost.",
            },
            {
                "slug": "path-concatenation",
                "explanation": "Building paths with string `+` breaks across platforms and "
                "on trailing separators. Use `pathlib.Path` and the `/` operator.",
            },
        ),
    ),
    ConceptSpec(
        slug="json-data",
        name="JSON",
        description="Serialising and parsing JSON; the mapping between JSON and Python types.",
        category="files",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.45,
        prerequisites=("dictionaries", "file-io"),
    ),
    ConceptSpec(
        slug="csv-data",
        name="CSV",
        description="Reading and writing delimited data with the csv module.",
        category="files",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.45,
        prerequisites=("file-io",),
    ),
    ConceptSpec(
        slug="regex",
        name="Regular expressions",
        description="Pattern matching for text extraction and validation.",
        category="files",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.65,
        prerequisites=("strings",),
    ),
    # -- APIs & services ----------------------------------------------------
    ConceptSpec(
        slug="http-basics",
        name="HTTP fundamentals",
        description="Requests, responses, methods, headers and status codes.",
        category="apis",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.55,
        weight=1.4,
        prerequisites=("json-data",),
        misconceptions=(
            {
                "slug": "unchecked-status",
                "explanation": "A 404 or 500 is still a response. If you don't check the "
                "status code, you'll parse an error page as data.",
            },
            {
                "slug": "missing-timeout",
                "explanation": "An HTTP call with no timeout can hang for ever, taking your "
                "worker with it. Always pass one.",
            },
        ),
    ),
    ConceptSpec(
        slug="api-clients",
        name="API clients",
        description="Building resilient clients: auth, retries, pagination and rate limits.",
        category="apis",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.7,
        prerequisites=("http-basics", "exceptions"),
    ),
    ConceptSpec(
        slug="rest-services",
        name="Building REST services",
        description="Routing, validation, status codes and error contracts.",
        category="apis",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.75,
        prerequisites=("api-clients", "classes"),
    ),
    ConceptSpec(
        slug="databases",
        name="Databases and SQL",
        description="Tables, keys, joins, transactions and parameterised queries.",
        category="databases",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.7,
        weight=1.3,
        prerequisites=("classes",),
        misconceptions=(
            {
                "slug": "sql-injection",
                "explanation": "Never build SQL with f-strings or concatenation. Use query "
                "parameters — the driver escapes them and the query plan gets cached too.",
            },
        ),
    ),
    # -- testing & quality --------------------------------------------------
    ConceptSpec(
        slug="unit-testing",
        name="Unit testing",
        description="Writing tests that pin down behaviour and catch regressions.",
        category="testing",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.55,
        weight=1.6,
        prerequisites=("functions", "exceptions"),
        misconceptions=(
            {
                "slug": "testing-implementation",
                "explanation": "Tests that assert on internals break whenever you refactor. "
                "Assert on observable behaviour instead.",
            },
        ),
    ),
    ConceptSpec(
        slug="test-design",
        name="Test design",
        description="Fixtures, parametrisation, mocking and test architecture.",
        category="testing",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.7,
        prerequisites=("unit-testing",),
    ),
    ConceptSpec(
        slug="logging",
        name="Logging and observability",
        description="Levels, handlers, structured logs and correlation ids.",
        category="automation",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.5,
        prerequisites=("functions",),
    ),
    ConceptSpec(
        slug="automation-design",
        name="Automation design",
        description="Idempotency, retries, checkpointing and safe failure for unattended jobs.",
        category="automation",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.75,
        weight=1.4,
        prerequisites=("file-io", "exceptions", "logging"),
    ),
    ConceptSpec(
        slug="cli-design",
        name="Command-line interfaces",
        description="argparse, exit codes, and designing a tool other people can use.",
        category="automation",
        level=SkillLevel.INTERMEDIATE,
        difficulty=0.5,
        prerequisites=("functions",),
    ),
    ConceptSpec(
        slug="concurrency",
        name="Concurrency",
        description="Threads, processes and asyncio — and which one a workload needs.",
        category="advanced",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.85,
        prerequisites=("functions", "http-basics"),
    ),
    ConceptSpec(
        slug="security-basics",
        name="Secure Python",
        description="Secrets, input validation, injection and safe deserialisation.",
        category="automation",
        level=SkillLevel.PROFESSIONAL,
        difficulty=0.7,
        prerequisites=("file-io", "databases"),
    ),
    ConceptSpec(
        slug="performance",
        name="Performance",
        description="Big-O intuition, profiling before optimising, and choosing data structures.",
        category="advanced",
        level=SkillLevel.ADVANCED,
        difficulty=0.75,
        prerequisites=("lists", "dictionaries"),
    ),
)

CONCEPTS_BY_SLUG = {concept.slug: concept for concept in CONCEPTS}
