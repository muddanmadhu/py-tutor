"""Module 03–04: functions and collections, plus error handling.

The step from "writes scripts" to "writes programs" is here: naming behaviour,
choosing a data structure deliberately, and failing well.
"""

from __future__ import annotations

from app.content.schema import Example, ExerciseSpec, HintSpec, LessonSpec, ModuleSpec
from app.models.enums import ExerciseKind, GraderKind, SkillLevel

# ---------------------------------------------------------------------------
# Lesson 5 — Functions
# ---------------------------------------------------------------------------

FUNCTIONS = LessonSpec(
    slug="functions",
    title="Functions: Naming a Piece of Behaviour",
    summary="Parameters, arguments, return values, scope, and the mutable-default trap that "
    "catches everyone once.",
    level=SkillLevel.BEGINNER,
    estimated_minutes=30,
    xp_reward=30,
    concepts=("functions", "scope", "args-kwargs", "type-hints"),
    reference_keys=("len", "sorted", "sum"),
    body="""\
## Why functions exist

A function is a name for a piece of behaviour. That is the whole idea, and it
buys three things at once: you stop repeating yourself, you can test the piece
in isolation, and the call site starts to read like a description of intent
rather than a pile of mechanics.

```python
def average(numbers: list[float]) -> float:
    \"\"\"Return the arithmetic mean of a non-empty sequence.\"\"\"
    return sum(numbers) / len(numbers)
```

* `def` starts a definition. Nothing runs yet.
* `numbers` is a **parameter** — a name that exists inside the function.
* `average([1, 2, 3])` passes `[1, 2, 3]` as the **argument**.
* `return` hands a value back to the caller and ends the function.

A function with no `return` returns `None`. Printing is not returning: you
cannot store, test or compose a print.

## Function vs method vs callable

These three are the same mechanism seen from different angles, and the
distinction matters when you read a traceback:

```python
len("hello")          # function  — free-standing, takes its subject as an argument
"hello".upper()       # method    — a function that belongs to an object; the object
                      #             is passed automatically as the first parameter
adder = Adder(10)
adder(5)              # callable  — an object whose class defines __call__
```

A method is just a function stored on a class. `"hello".upper()` is
`str.upper("hello")` with nicer syntax. That is exactly why instance methods
declare `self` first: it is the object the method was reached through.

## Arguments, in the order Python accepts them

```python
def create_user(
    name,                    # positional-or-keyword, required
    email,
    role="learner",          # default → optional
    *tags,                   # extra positional args, collected into a tuple
    active=True,             # keyword-only (it follows *tags)
    **metadata,              # extra keyword args, collected into a dict
):
    ...

create_user("Ada", "ada@example.com", "admin", "vip", "beta", active=False, team="core")
```

* `*args` collects surplus positional arguments into a tuple.
* `**kwargs` collects surplus keyword arguments into a dict.
* Anything after `*args` (or a bare `*`) can only be passed by keyword — which
  is a good way to force call sites to be readable:

```python
def resize(image, *, width, height):   # resize(img, width=800, height=600)
```

## The mutable default trap

```python
def add_item(item, basket=[]):     # ← wrong, and it will bite you
    basket.append(item)
    return basket

add_item("apple")     # ['apple']
add_item("pear")      # ['apple', 'pear']   ← where did the apple come from?
```

Default values are evaluated **once**, when the `def` line executes — not on
each call. Every call that omits `basket` shares one list. The fix is always the
same:

```python
def add_item(item, basket=None):
    if basket is None:
        basket = []
    basket.append(item)
    return basket
```

## Scope: the LEGB rule

Python resolves a name by looking, in order, at **L**ocal → **E**nclosing →
**G**lobal → **B**uilt-in.

```python
total = 0            # global

def add(n):
    total = total + n    # UnboundLocalError
```

Assigning to `total` anywhere in the function makes it local *throughout* the
function — including on the line that reads it before assignment. The honest
fix is not `global`; it is to return the value:

```python
def add(total, n):
    return total + n
```

Reach for `global` almost never. Functions that mutate module state are
functions you cannot test in isolation.

## Docstrings and type hints

```python
def parse_duration(text: str) -> int:
    \"\"\"Convert '1h30m' into seconds.

    Raises
    ------
    ValueError
        If the text is not a recognised duration.
    \"\"\"
```

Type hints do not change runtime behaviour — Python does not enforce them. They
exist for readers and for tools (mypy, your editor). On a codebase of any size
they pay for themselves within a week.
""",
    sections={
        "what_is_it": "A function binds a name to a reusable block of behaviour that takes "
        "inputs (parameters) and produces an output (a return value).",
        "why_it_exists": "To remove duplication, to make behaviour testable in isolation, and "
        "to let a reader understand a call site without reading the implementation.",
        "how_it_works": "`def` creates a function object and binds it to a name. Calling it "
        "pushes a new stack frame with a fresh local namespace, runs the body, and pops the "
        "frame when `return` (or the end of the body) is reached. Defaults are evaluated once, "
        "at definition time.",
        "when_to_use": "When logic is used more than once; when a block needs a name to be "
        "understandable; when you want to unit-test a piece of behaviour.",
        "when_not_to_use": "Do not extract a function for a single trivial line used once — "
        "the indirection costs more than it saves. Avoid functions with many parameters and "
        "no cohesion; that is a class or a dataclass.",
        "common_mistakes": "Mutable default arguments; printing instead of returning; "
        "forgetting that a bare `return` (or falling off the end) yields None; "
        "UnboundLocalError from assigning to a global; too many parameters; side effects "
        "hidden inside a function that looks pure.",
        "real_world": "Every API handler, every data transform and every test is a function. "
        "The rule that matters in production code is *one job per function*: it makes failures "
        "localisable and tests small.",
        "alternatives": "A class when behaviour needs state across calls; a module-level "
        "constant when the 'function' just returns a fixed value; a comprehension when the "
        "function only maps or filters.",
        "performance": "A call costs roughly 50–100 ns. That is irrelevant except in the "
        "innermost loop of a hot path — and if you are there, the fix is usually a better "
        "algorithm, not fewer functions. `functools.lru_cache` makes repeated calls with the "
        "same arguments free.",
        "security": "Validate arguments at trust boundaries rather than assuming callers "
        "behaved. Never accept a callable from untrusted input and call it. Be careful what "
        "you put in default arguments — they are visible in `__defaults__` and in docs.",
    },
    starter_code='''\
def greet(name: str, greeting: str = "Hello") -> str:
    """Return a greeting for the given name."""
    return f"{greeting}, {name}!"


print(greet("Ada"))
print(greet("Grace", greeting="Welcome"))
''',
    examples=(
        Example(
            title="The mutable default trap, demonstrated",
            code="""\
def broken(item, basket=[]):
    basket.append(item)
    return basket


def fixed(item, basket=None):
    if basket is None:
        basket = []
    basket.append(item)
    return basket


print(broken("a"), broken("b"))
print(fixed("a"), fixed("b"))
""",
            output="['a', 'b'] ['a', 'b']\n['a'] ['b']",
            explanation="Both calls to `broken` printed the same shared list. Note the first "
            "printed value is already polluted — the list is one object created at "
            "definition time.",
        ),
        Example(
            title="*args and **kwargs",
            code="""\
def describe(*args, **kwargs):
    print("positional:", args)
    print("keyword:   ", kwargs)


describe(1, 2, 3, mode="fast", retries=2)
""",
            output="positional: (1, 2, 3)\nkeyword:    {'mode': 'fast', 'retries': 2}",
            explanation="`args` is a tuple, `kwargs` a dict. Unpacking works in reverse: "
            "`describe(*[1,2], **{'mode':'fast'})`.",
        ),
        Example(
            title="Function, method, callable",
            code="""\
class Multiplier:
    def __init__(self, factor):
        self.factor = factor

    def __call__(self, value):
        return value * self.factor


double = Multiplier(2)

print(len([1, 2, 3]))     # function
print("abc".upper())      # method
print(double(21))         # callable object
print(callable(double), callable(len), callable(42))
""",
            output="3\nABC\n42\nTrue True False",
            explanation="`callable()` asks 'can this be invoked?'. Functions, methods, "
            "classes and objects defining `__call__` all qualify.",
        ),
    ),
    visualizations=(
        {
            "kind": "stack",
            "title": "Call stack during a nested call",
            "frames": [
                {"name": "<module>", "locals": {"data": "[1, 2, 3]"}},
                {"name": "average(numbers)", "locals": {"numbers": "[1, 2, 3]"}},
                {"name": "sum(iterable)", "locals": {"iterable": "[1, 2, 3]"}},
            ],
        },
    ),
    exercises=(
        ExerciseSpec(
            slug="functions-stats",
            title="A small statistics toolkit",
            prompt="""\
Implement three functions:

* `mean(values)` — arithmetic mean; raise `ValueError` on an empty sequence
* `median(values)` — middle value; the average of the middle two when the count
  is even; raise `ValueError` on an empty sequence
* `summarise(values)` — return a dict `{"count", "mean", "median", "min", "max"}`;
  return `{"count": 0}` for an empty sequence rather than raising

None of them may modify the list they are given.
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.BEGINNER,
            difficulty=0.5,
            estimated_minutes=18,
            xp_reward=40,
            starter_files={
                "main.py": '''\
def mean(values: list[float]) -> float:
    """Return the arithmetic mean."""
    ...


def median(values: list[float]) -> float:
    """Return the median value."""
    ...


def summarise(values: list[float]) -> dict:
    """Return count, mean, median, min and max."""
    ...
'''
            },
            hidden_files={
                "test_stats.py": """\
import pytest

from main import mean, median, summarise


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_mean_empty_raises():
    with pytest.raises(ValueError):
        mean([])


def test_median_odd():
    assert median([5, 1, 3]) == 3


def test_median_even():
    assert median([4, 1, 3, 2]) == 2.5


def test_median_empty_raises():
    with pytest.raises(ValueError):
        median([])


def test_does_not_mutate_input():
    data = [3, 1, 2]
    median(data)
    assert data == [3, 1, 2], "median must not sort the caller's list in place"


def test_summarise():
    result = summarise([2, 4, 6])
    assert result["count"] == 3
    assert result["mean"] == 4
    assert result["median"] == 4
    assert result["min"] == 2
    assert result["max"] == 6


def test_summarise_empty():
    assert summarise([]) == {"count": 0}
"""
            },
            concepts=("functions", "lists", "exceptions"),
            hints=(
                HintSpec(
                    "Three separate jobs, three separate functions. `summarise` should "
                    "call the other two rather than repeat their logic."
                ),
                HintSpec(
                    "For the median you need the values in order — but the test insists "
                    "the caller's list is untouched. Which of `sorted()` and `.sort()` "
                    "leaves the original alone?"
                ),
                HintSpec(
                    "With an even count there is no single middle element. With "
                    "`n = len(values)`, the two middle indexes are `n // 2 - 1` and "
                    "`n // 2`."
                ),
                HintSpec(
                    "```python\ndef median(values):\n    if not values:\n"
                    "        raise ValueError('median of empty sequence')\n"
                    "    ordered = sorted(values)\n    n = len(ordered)\n"
                    "    middle = n // 2\n    if n % 2 == 1:\n        return ordered[middle]\n"
                    "    return (ordered[middle - 1] + ordered[middle]) / 2\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
def mean(values: list[float]) -> float:
    """Return the arithmetic mean.

    Raises
    ------
    ValueError
        If ``values`` is empty — the mean of nothing is undefined, and returning
        0 would silently corrupt any calculation downstream.
    """
    if not values:
        raise ValueError("mean of an empty sequence is undefined")
    return sum(values) / len(values)


def median(values: list[float]) -> float:
    """Return the median value without modifying the input."""
    if not values:
        raise ValueError("median of an empty sequence is undefined")
    ordered = sorted(values)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def summarise(values: list[float]) -> dict:
    """Return count, mean, median, min and max.

    Unlike ``mean`` and ``median`` this tolerates an empty sequence: a summary
    of no data is legitimately "no data", not an error.
    """
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean": mean(values),
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }
'''
            },
            solution_explanation="Note the deliberate inconsistency: `mean` raises on empty "
            "input while `summarise` returns `{'count': 0}`. That is not sloppiness — a "
            "summary of an empty dataset is meaningful, an average of nothing is not. "
            "Deciding *per function* whether an empty input is an error is an API design "
            "decision, and worth making explicitly.",
            misconception_rules=(
                {"pattern": "must not sort the caller", "misconception": "sort-returns-none"},
                {"pattern": "DID NOT RAISE", "misconception": "missing-validation"},
            ),
        ),
        ExerciseSpec(
            slug="functions-mutable-default",
            title="Debug: the shared basket",
            prompt="""\
`add_to_cart` is supposed to start a fresh cart when none is supplied. In
production, a customer reported seeing another customer's items.

Find the defect and fix it. Do not change the signature's *behaviour* from the
caller's point of view — `add_to_cart("apple")` must still work.
""",
            kind=ExerciseKind.DEBUG,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.5,
            estimated_minutes=10,
            xp_reward=40,
            starter_files={
                "main.py": '''\
def add_to_cart(item: str, cart: list[str] = []) -> list[str]:
    """Add an item to a cart, creating a new cart when none is given."""
    cart.append(item)
    return cart
'''
            },
            hidden_files={
                "test_cart.py": """\
from main import add_to_cart


def test_new_cart_each_time():
    first = add_to_cart("apple")
    second = add_to_cart("pear")
    assert first == ["apple"]
    assert second == ["pear"]
    assert first is not second


def test_existing_cart_is_extended():
    cart = ["bread"]
    result = add_to_cart("milk", cart)
    assert result == ["bread", "milk"]
    assert result is cart


def test_repeated_default_calls_stay_independent():
    carts = [add_to_cart(f"item-{n}") for n in range(5)]
    assert all(len(cart) == 1 for cart in carts)
"""
            },
            concepts=("functions", "mutability", "debugging"),
            hints=(
                HintSpec(
                    "When is the default value `[]` actually created — once, or on every call?"
                ),
                HintSpec(
                    "Defaults are evaluated when the `def` statement runs. Every call "
                    "that omits the argument therefore shares one object."
                ),
                HintSpec(
                    "The sentinel pattern fixes this: use an immutable default that "
                    "means 'nothing was passed', and create the real value inside."
                ),
                HintSpec(
                    "```python\ndef add_to_cart(item, cart=None):\n"
                    "    if cart is None:\n        cart = []\n    ...\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
def add_to_cart(item: str, cart: list[str] | None = None) -> list[str]:
    """Add an item to a cart, creating a new cart when none is given.

    ``None`` is used as the default sentinel because a mutable default would be
    created once at definition time and then shared by every call that omits it.
    """
    if cart is None:
        cart = []
    cart.append(item)
    return cart
'''
            },
            solution_explanation="`None` as a sentinel is the standard Python idiom for "
            "'no argument supplied'. The type hint `list[str] | None` documents it. This bug "
            "is famous precisely because it does not fail immediately — the first call looks "
            "fine, and the corruption accumulates.",
            misconception_rules=(
                {"pattern": "test_new_cart_each_time", "misconception": "mutable-default"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 6 — Lists
# ---------------------------------------------------------------------------

LISTS = LessonSpec(
    slug="lists",
    title="Lists: Ordered, Mutable, Everywhere",
    summary="Indexing, slicing, the mutation methods, and the copy semantics that decide "
    "whether your change is visible somewhere else.",
    level=SkillLevel.BEGINNER,
    estimated_minutes=28,
    concepts=("lists", "mutability", "comprehensions"),
    reference_keys=("list.append", "list.sort", "sorted", "list.pop"),
    body="""\
## Indexing and slicing

```python
letters = ["a", "b", "c", "d", "e"]

letters[0]        # 'a'      first
letters[-1]       # 'e'      last — no len() arithmetic needed
letters[1:4]      # ['b','c','d']    start inclusive, stop exclusive
letters[:3]       # ['a','b','c']
letters[::2]      # ['a','c','e']    every second
letters[::-1]     # reversed copy
```

A slice always produces a **new list**. `letters[:]` is therefore the classic
shallow copy — though `letters.copy()` says so more clearly.

Indexing out of range raises `IndexError`. Slicing out of range does not — it
clamps. `letters[10:20]` is `[]`. This asymmetry is deliberate and occasionally
useful, but it means a slicing bug can be silent where an indexing bug is loud.

## The method vocabulary

| Method | Effect | Returns |
| --- | --- | --- |
| `append(x)` | add one item at the end | `None` |
| `extend(iterable)` | add every item from an iterable | `None` |
| `insert(i, x)` | insert before index `i` | `None` |
| `remove(x)` | delete the first `x`; `ValueError` if absent | `None` |
| `pop(i=-1)` | remove and return the item at `i` | the item |
| `sort(key=…, reverse=…)` | sort **in place** | `None` |
| `reverse()` | reverse in place | `None` |
| `index(x)` | position of the first `x` | int |
| `count(x)` | how many times `x` appears | int |
| `copy()` | shallow copy | new list |
| `clear()` | remove everything | `None` |

Notice how many return `None`. That is the source of Python's most common
one-line bug:

```python
names = names.sort()      # names is now None
names = sorted(names)     # what you meant
```

The convention is consistent across Python: **methods that mutate return None**,
so you cannot mistake mutation for a fresh value.

`append` vs `extend` is the other classic:

```python
a = [1, 2]
a.append([3, 4])    # [1, 2, [3, 4]]   one new element, which is a list
a.extend([3, 4])    # [1, 2, 3, 4]     two new elements
```

## Sorting with a key

```python
people = [{"name": "Ada", "age": 36}, {"name": "Bob", "age": 24}]

by_age = sorted(people, key=lambda p: p["age"])
by_name_desc = sorted(people, key=lambda p: p["name"], reverse=True)
by_age_then_name = sorted(people, key=lambda p: (p["age"], p["name"]))
```

`key` is called once per element, and the results are compared. Returning a
tuple gives multi-level sorting for free. Python's sort is *stable*: equal
elements keep their original order, which is why sorting twice (secondary key
first) also works.

## Copying: shallow is not deep

```python
import copy

grid = [[0, 0], [0, 0]]
shallow = grid.copy()
shallow[0][0] = 9
print(grid)          # [[9, 0], [0, 0]]  ← the inner lists are shared

deep = copy.deepcopy(grid)
deep[0][0] = 7
print(grid)          # unchanged
```

A shallow copy duplicates the outer container and copies *references* to the
contents. If everything inside is immutable, that is indistinguishable from a
deep copy — which is why this bug hides until nesting appears.

## Comprehensions

```python
squares      = [n * n for n in range(10)]
evens        = [n for n in range(20) if n % 2 == 0]
names_upper  = [user["name"].upper() for user in users if user["active"]]
```

Read it left to right as: *the expression, for each item, where the condition
holds*. Comprehensions are faster than the equivalent `for` + `append` loop
because the append is done at C level.

Stop at one level of nesting. If you need two `for` clauses and a condition, a
loop is kinder to the next reader.
""",
    sections={
        "what_is_it": "A list is an ordered, mutable sequence of arbitrary objects, "
        "implemented as a dynamic array of pointers.",
        "why_it_exists": "It is the default 'a bunch of things, in order' container: cheap "
        "appends, cheap indexing, and it can hold anything.",
        "how_it_works": "CPython stores a contiguous array of object pointers with spare "
        "capacity, growing geometrically when full. Indexing is O(1); appending is amortised "
        "O(1); inserting or deleting at the front is O(n) because everything must shift.",
        "when_to_use": "Ordered data, sequences you will append to or iterate, and anything "
        "where position carries meaning.",
        "when_not_to_use": "Membership testing in a large collection (use a `set` — O(1) "
        "instead of O(n)); fixed records where position means a field (use a tuple, "
        "NamedTuple or dataclass); frequent insertion at the front (use "
        "`collections.deque`); large numeric arrays (use `array` or NumPy).",
        "common_mistakes": "`x = x.sort()` (None); confusing `append` with `extend`; "
        "modifying a list while iterating it; assuming `b = a` copies; assuming `a.copy()` "
        "copies nested structures; using `list` as a variable name and shadowing the built-in.",
        "real_world": "Query results, parsed CSV rows, batches of jobs, accumulated errors — "
        "lists are the workhorse. In pipelines the usual pattern is: read into a list, "
        "transform with comprehensions, write out.",
        "alternatives": "tuple (immutable, hashable), set (unique, fast membership), deque "
        "(fast at both ends), array/NumPy (compact numerics), generator (lazy, constant "
        "memory over a large stream).",
        "performance": "`x in some_list` is O(n) — converting to a set first turns a "
        "quadratic loop into a linear one, which is the single highest-value optimisation a "
        "beginner can learn. `list.insert(0, x)` and `list.pop(0)` are O(n). Building a "
        "string by `+=` in a loop is quadratic; use `''.join(parts)`.",
        "security": "Never let external input decide an unbounded allocation size — "
        "`[0] * user_supplied_n` is a memory exhaustion vector. When lists come from parsed "
        "input, validate the length before processing.",
    },
    starter_code="""\
inventory = ["widget", "gadget", "doohickey"]

inventory.append("sprocket")
inventory.sort()

print(inventory)
print("First:", inventory[0], "| Last:", inventory[-1])
print("Uppercase:", [item.upper() for item in inventory])
""",
    examples=(
        Example(
            title="Mutating methods return None",
            code="""\
values = [3, 1, 2]
result = values.sort()
print("returned:", result)
print("list is now:", values)
print("sorted() gives a new list:", sorted([3, 1, 2]))
""",
            output="returned: None\nlist is now: [1, 2, 3]\nsorted() gives a new list: [1, 2, 3]",
            explanation="`sort()` mutates and returns None; `sorted()` leaves the input alone "
            "and returns a new list. Choose based on whether the caller's list should change.",
        ),
        Example(
            title="Shallow vs deep copy",
            code="""\
import copy

original = [[1, 2], [3, 4]]
shallow = original.copy()
deep = copy.deepcopy(original)

shallow[0].append(99)
deep[1].append(77)

print("original:", original)
print("shallow: ", shallow)
print("deep:    ", deep)
""",
            output="original: [[1, 2, 99], [3, 4]]\nshallow:  [[1, 2, 99], [3, 4]]\n"
            "deep:     [[1, 2], [3, 4, 77]]",
            explanation="The shallow copy shares inner lists with the original; the deep copy "
            "does not.",
        ),
        Example(
            title="set membership vs list membership",
            code="""\
import time

haystack_list = list(range(200_000))
haystack_set = set(haystack_list)

start = time.perf_counter()
199_999 in haystack_list
list_time = time.perf_counter() - start

start = time.perf_counter()
199_999 in haystack_set
set_time = time.perf_counter() - start

print(f"list scan is roughly {list_time / max(set_time, 1e-9):.0f}x slower")
""",
            output="list scan is roughly 1000x slower",
            explanation="Exact numbers vary by machine, but the shape does not: list "
            "membership is a linear scan, set membership is a hash lookup.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="lists-top-performers",
            title="Rank the top performers",
            prompt="""\
Implement `top_performers(records, limit=3)`.

`records` is a list of dicts like `{"name": "Ada", "sales": 120}`.

Return a list of the `limit` highest-selling names, ordered by sales descending.
Break ties alphabetically by name. Do not modify the input list.
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.5,
            estimated_minutes=14,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def top_performers(records: list[dict], limit: int = 3) -> list[str]:
    """Return the names of the top `limit` sellers."""
    ...
'''
            },
            hidden_files={
                "test_top.py": """\
from main import top_performers

RECORDS = [
    {"name": "Ada", "sales": 120},
    {"name": "Bob", "sales": 300},
    {"name": "Cleo", "sales": 300},
    {"name": "Dan", "sales": 50},
]


def test_orders_by_sales_desc():
    assert top_performers(RECORDS, limit=2) == ["Bob", "Cleo"]


def test_ties_broken_alphabetically():
    tied = [
        {"name": "Zoe", "sales": 10},
        {"name": "Amy", "sales": 10},
    ]
    assert top_performers(tied, limit=2) == ["Amy", "Zoe"]


def test_default_limit_is_three():
    assert len(top_performers(RECORDS)) == 3


def test_limit_larger_than_data():
    assert len(top_performers(RECORDS, limit=99)) == 4


def test_input_not_modified():
    snapshot = [dict(record) for record in RECORDS]
    top_performers(RECORDS)
    assert RECORDS == snapshot


def test_empty():
    assert top_performers([]) == []
"""
            },
            concepts=("lists", "comprehensions", "functions"),
            hints=(
                HintSpec(
                    "Two steps: put the records in the right order, then take the names "
                    "of the first `limit` of them."
                ),
                HintSpec(
                    "`sorted()` returns a new list, which is what the "
                    "'do not modify' requirement needs."
                ),
                HintSpec(
                    "A tuple key sorts on several fields. You want sales descending but "
                    "name ascending — those pull in opposite directions, so `reverse=True` "
                    "alone will not do it. Negate the numeric field instead."
                ),
                HintSpec(
                    "```python\nordered = sorted(records, key=lambda r: (-r['sales'], r['name']))\n"
                    "return [r['name'] for r in ordered[:limit]]\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
def top_performers(records: list[dict], limit: int = 3) -> list[str]:
    """Return the names of the top `limit` sellers.

    Sorted by sales descending, ties broken alphabetically. The input list is
    left untouched: ``sorted`` returns a new list, and slicing copies again.
    """
    ordered = sorted(records, key=lambda record: (-record["sales"], record["name"]))
    return [record["name"] for record in ordered[:limit]]
'''
            },
            solution_explanation="Negating the numeric field is the standard way to sort one "
            "key descending and another ascending in a single pass. `reverse=True` would "
            "reverse *both*, putting 'Zoe' before 'Amy'. Slicing beyond the end is safe, which "
            "is why `limit=99` needs no special case.",
            misconception_rules=(
                {"pattern": "test_ties_broken", "misconception": "sort-key-direction"},
                {"pattern": "test_input_not_modified", "misconception": "aliasing"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 7 — Dictionaries
# ---------------------------------------------------------------------------

DICTIONARIES = LessonSpec(
    slug="dictionaries",
    title="Dictionaries: Lookup by Meaning",
    summary="Key–value mapping, the .get() idiom, counting patterns, and why dict lookup is O(1).",
    level=SkillLevel.BEGINNER,
    estimated_minutes=26,
    concepts=("dictionaries", "sets", "comprehensions", "tuples"),
    reference_keys=("dict.get", "dict.items", "dict.setdefault"),
    body="""\
## A dict maps keys to values

```python
user = {"name": "Ada", "role": "engineer", "active": True}

user["name"]              # 'Ada'
user["email"]             # KeyError
user.get("email")         # None
user.get("email", "n/a")  # 'n/a'
```

`d[key]` says *this key must be here* — a KeyError is then a genuine bug report.
`d.get(key, default)` says *it might not be*. Choosing between them is a
statement about your data, so choose deliberately rather than defaulting to
`.get` everywhere; a silent `None` flowing downstream is harder to debug than a
KeyError at the source.

## Iteration

```python
for key in user:                   # keys
for value in user.values():        # values
for key, value in user.items():    # both — the one you usually want
```

Since Python 3.7, dicts preserve insertion order. That is a language guarantee,
not an implementation detail, so you may rely on it.

## Building and updating

```python
counts = {}
counts["a"] = counts.get("a", 0) + 1        # the counting idiom

from collections import defaultdict, Counter
counts = defaultdict(int); counts["a"] += 1  # no get() needed
Counter("mississippi").most_common(2)        # [('i', 4), ('s', 4)]

merged = {**defaults, **overrides}           # right-hand side wins
merged = defaults | overrides                # same thing, 3.9+
```

`setdefault` is the one-liner for grouping:

```python
groups = {}
for user in users:
    groups.setdefault(user["role"], []).append(user["name"])
```

## Keys must be hashable

```python
{"a": 1}          # str key      ✓
{(1, 2): "point"} # tuple key    ✓  (tuples of immutables are hashable)
{[1, 2]: "nope"}  # TypeError: unhashable type: 'list'
```

A hashable object has a `__hash__` that never changes. Mutable containers are
deliberately unhashable: if you could use a list as a key and then mutate it,
the dict would lose track of it. This is the same rule that governs set members.

## Why lookup is O(1)

A dict is a hash table. Python computes `hash(key)`, uses it to jump straight to
a slot, and compares. That is why `key in dict` is constant time regardless of
size, while `value in list` is linear. Choosing a dict or set over a list for
membership testing is the most common real-world performance fix there is.

## Dict comprehensions

```python
{name: len(name) for name in names}
{k: v for k, v in config.items() if v is not None}
inverted = {value: key for key, value in mapping.items()}
```

Inverting only works when the values are unique and hashable — otherwise later
entries silently overwrite earlier ones.

## Dispatch tables

A dict of functions replaces a long if/elif chain:

```python
handlers = {"csv": load_csv, "json": load_json, "xml": load_xml}

handler = handlers.get(extension)
if handler is None:
    raise ValueError(f"unsupported format: {extension}")
return handler(path)
```

Adding a format is now a one-line dict entry rather than an edit to a growing
conditional.
""",
    sections={
        "what_is_it": "A dict is a mutable mapping from hashable keys to arbitrary values, "
        "implemented as a hash table with guaranteed insertion order.",
        "why_it_exists": "To look things up by meaning rather than by position. Position is "
        "an accident of storage; a key is a name.",
        "how_it_works": "`hash(key)` selects a slot in an open-addressed table; collisions "
        "probe onwards. Average lookup, insert and delete are O(1). Since 3.6 the "
        "implementation is compact and ordered, and since 3.7 that ordering is guaranteed.",
        "when_to_use": "Any key→value association: configuration, caches, counters, grouping, "
        "records parsed from JSON, dispatch tables.",
        "when_not_to_use": "When the keys are a fixed, known set — a dataclass or NamedTuple "
        "gives you attribute access, type checking and typo protection. When you only need "
        "membership, a set is smaller and clearer. When order-by-value matters, sort into a "
        "list of tuples.",
        "common_mistakes": "Assuming a key exists (KeyError); using a list as a key; "
        "inverting a dict with duplicate values and silently losing entries; mutating a dict "
        "while iterating it (RuntimeError); reaching for `.get()` reflexively and turning a "
        "loud bug into a quiet None.",
        "real_world": "JSON maps directly onto dicts, so every API response you parse is a "
        "dict. Configuration, feature flags, request headers, database rows and caches are "
        "all dicts. Dispatch tables are how plugin systems avoid giant conditionals.",
        "alternatives": "`collections.Counter` for tallies; `defaultdict` for grouping; "
        "`types.MappingProxyType` for a read-only view; `dataclass` for fixed schemas; "
        "`TypedDict` when you want a dict but with type checking.",
        "performance": "O(1) average lookup, but with a constant factor and memory overhead "
        "well above a list. Converting a list to a set/dict for membership testing pays for "
        "itself above roughly a hundred lookups. `dict.get` is slightly slower than `d[k]` "
        "because of the extra default handling — irrelevant except in a hot loop.",
        "security": "Never build a dict of unbounded size from untrusted input — that is a "
        "memory exhaustion vector. Be aware that keys derived from user input can be used for "
        "hash-collision attacks in some contexts; Python randomises string hashing per process "
        "(`PYTHONHASHSEED`) to mitigate this.",
    },
    starter_code="""\
sales = {"Ada": 120, "Bob": 300, "Cleo": 90}

for name, amount in sales.items():
    print(f"{name:<6} {amount:>5}")

print("Total:", sum(sales.values()))
print("Best: ", max(sales, key=sales.get))
print("Missing person:", sales.get("Zoe", 0))
""",
    examples=(
        Example(
            title="Three ways to count",
            code="""\
from collections import Counter, defaultdict

text = "mississippi"

manual = {}
for char in text:
    manual[char] = manual.get(char, 0) + 1

grouped = defaultdict(int)
for char in text:
    grouped[char] += 1

print(manual)
print(dict(grouped))
print(Counter(text).most_common(2))
""",
            output="{'m': 1, 'i': 4, 's': 4, 'p': 2}\n{'m': 1, 'i': 4, 's': 4, 'p': 2}\n"
            "[('i', 4), ('s', 4)]",
            explanation="All three are correct. `Counter` is the one to reach for when the "
            "task really is counting.",
        ),
        Example(
            title="Grouping with setdefault",
            code="""\
people = [
    {"name": "Ada", "team": "core"},
    {"name": "Bob", "team": "ops"},
    {"name": "Cleo", "team": "core"},
]

teams = {}
for person in people:
    teams.setdefault(person["team"], []).append(person["name"])

print(teams)
""",
            output="{'core': ['Ada', 'Cleo'], 'ops': ['Bob']}",
            explanation="`setdefault` returns the existing list, or inserts and returns a new "
            "one. One line instead of a membership check plus an assignment.",
        ),
        Example(
            title="KeyError vs get",
            code="""\
config = {"host": "localhost"}

print(config.get("port", 8000))
try:
    print(config["port"])
except KeyError as exc:
    print("KeyError for", exc)
""",
            output="8000\nKeyError for 'port'",
            explanation="Use `.get` with a default when absence is expected; let the KeyError "
            "fly when absence means someone misconfigured the system.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="dicts-word-frequency",
            title="Word frequency report",
            prompt="""\
Implement `word_frequencies(text, top_n=None)`.

* split on whitespace
* strip surrounding punctuation (`.,!?;:"'()`) from each word
* compare case-insensitively
* ignore anything that is empty after stripping
* return a dict of `word -> count`, ordered most frequent first, ties broken
  alphabetically
* when `top_n` is given, return only that many entries
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.55,
            estimated_minutes=16,
            xp_reward=40,
            starter_files={
                "main.py": '''\
def word_frequencies(text: str, top_n: int | None = None) -> dict[str, int]:
    """Count words in `text`, most frequent first."""
    ...
'''
            },
            hidden_files={
                "test_words.py": """\
from main import word_frequencies


def test_counts_and_orders():
    result = word_frequencies("the cat the dog the bird cat")
    assert list(result.items())[0] == ("the", 3)
    assert result["cat"] == 2


def test_case_insensitive():
    assert word_frequencies("Cat cat CAT") == {"cat": 3}


def test_strips_punctuation():
    assert word_frequencies("hello, world! hello.") == {"hello": 2, "world": 1}


def test_ties_alphabetical():
    result = word_frequencies("beta alpha")
    assert list(result.keys()) == ["alpha", "beta"]


def test_top_n():
    result = word_frequencies("a a b b c", top_n=2)
    assert len(result) == 2
    assert "c" not in result


def test_empty_text():
    assert word_frequencies("") == {}


def test_punctuation_only_ignored():
    assert word_frequencies("... !!! ,") == {}
"""
            },
            concepts=("dictionaries", "strings", "loops"),
            hints=(
                HintSpec(
                    "Four separate concerns: split, clean each word, count, then order. "
                    "Do them in that sequence rather than all at once."
                ),
                HintSpec(
                    "`str.strip(chars)` removes any of the given characters from both "
                    "ends — pass all your punctuation as one string."
                ),
                HintSpec(
                    "For the ordering: `sorted(counts.items(), key=...)` with a tuple key "
                    "of (negative count, word) gives most-frequent-first with alphabetical "
                    "tie-breaking. Then rebuild a dict from the sorted pairs."
                ),
                HintSpec(
                    "```python\nPUNCTUATION = '.,!?;:\"\\'()'\ncounts = {}\n"
                    "for raw in text.split():\n    word = raw.strip(PUNCTUATION).lower()\n"
                    "    if not word:\n        continue\n"
                    "    counts[word] = counts.get(word, 0) + 1\n"
                    "ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
PUNCTUATION = ".,!?;:\\"'()"


def word_frequencies(text: str, top_n: int | None = None) -> dict[str, int]:
    """Count words in `text`, most frequent first, ties broken alphabetically.

    Dicts preserve insertion order (guaranteed since Python 3.7), so building
    the result from an ordered list of pairs is enough to make the ordering part
    of the returned value rather than something the caller has to redo.
    """
    counts: dict[str, int] = {}
    for raw_word in text.split():
        word = raw_word.strip(PUNCTUATION).lower()
        if not word:
            continue
        counts[word] = counts.get(word, 0) + 1

    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if top_n is not None:
        ordered = ordered[:top_n]
    return dict(ordered)
'''
            },
            solution_explanation="`counts.get(word, 0) + 1` is the canonical counting idiom; "
            "`collections.Counter` would do the same job in one line and is what you would "
            "reach for in production. The ordering relies on dicts preserving insertion order "
            "— a guarantee since 3.7, and the reason `dict(ordered)` is meaningful at all.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 8 — Exceptions
# ---------------------------------------------------------------------------

EXCEPTIONS = LessonSpec(
    slug="exceptions",
    title="Errors and Exceptions: Failing Well",
    summary="try/except/else/finally, choosing what to catch, raising deliberately, and why "
    "silent failure is worse than a crash.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=28,
    xp_reward=30,
    concepts=("exceptions", "custom-exceptions", "debugging"),
    reference_keys=("Exception", "ValueError", "try"),
    body="""\
## Read the traceback from the bottom

```
Traceback (most recent call last):
  File "app.py", line 42, in <module>
    total = compute(order)
  File "app.py", line 30, in compute
    return sum(item.price for item in order.items)
AttributeError: 'NoneType' object has no attribute 'items'
```

The **last line** is what went wrong: something was `None` when an object was
expected. The lines above are how you got there, oldest call first. Beginners
read from the top and drown; read bottom-up and the answer is usually in two
lines.

## The full shape

```python
try:
    value = int(user_input)
except ValueError:
    print("That wasn't a number")
else:
    print(f"Got {value}")     # runs only if NO exception was raised
finally:
    print("Always runs")      # cleanup — even on exception, even on return
```

* `except` handles a failure you anticipated.
* `else` holds the code that should only run on success. Putting it there
  instead of at the end of `try` means you are not accidentally catching
  exceptions from *it*.
* `finally` always runs. Use it for cleanup you cannot skip.

## Catch what you can handle

```python
try:
    config = json.loads(raw)
except Exception:            # ← too broad: hides typos, KeyboardInterrupt, everything
    config = {}
```

Broad handlers convert bugs into wrong behaviour. Catch the specific class:

```python
except json.JSONDecodeError:
    config = {}
```

And never write this:

```python
except SomeError:
    pass                     # the error happened; now nobody will ever know
```

If you truly can ignore a failure, say so and log it. `contextlib.suppress` is
the honest one-liner when you genuinely mean it:

```python
from contextlib import suppress
with suppress(FileNotFoundError):
    path.unlink()
```

## The hierarchy

```
BaseException
 ├── KeyboardInterrupt        ← catching this makes Ctrl-C stop working
 ├── SystemExit
 └── Exception                ← catch below here, if at all
      ├── ArithmeticError → ZeroDivisionError
      ├── LookupError     → IndexError, KeyError
      ├── OSError         → FileNotFoundError, PermissionError, TimeoutError
      ├── ValueError      → UnicodeDecodeError
      └── TypeError, AttributeError, ImportError, …
```

Catching `LookupError` handles both `IndexError` and `KeyError`. Catching
`BaseException` breaks Ctrl-C.

## Raising deliberately

```python
def withdraw(balance: float, amount: float) -> float:
    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount}")
    if amount > balance:
        raise InsufficientFunds(f"balance {balance} cannot cover {amount}")
    return balance - amount
```

An error message is a message to a person at 3am. `"invalid input"` helps nobody;
include the value that was wrong.

## Custom exceptions and chaining

```python
class PaymentError(Exception):
    \"\"\"Base for every payment failure.\"\"\"

class CardDeclined(PaymentError):
    \"\"\"The issuer refused the transaction.\"\"\"

try:
    charge(card)
except requests.Timeout as exc:
    raise PaymentError("payment gateway timed out") from exc
```

`raise ... from exc` preserves the original traceback under
*"The above exception was the direct cause of..."*. Without `from`, you lose the
root cause — and the root cause is the thing you actually need.

A small exception hierarchy per subsystem lets callers choose their granularity:
catch `PaymentError` for anything payment-related, or `CardDeclined` for one
specific case.

## EAFP over LBYL

```python
# Look Before You Leap — and race with anything that changes in between
if path.exists():
    data = path.read_text()

# Easier to Ask Forgiveness than Permission — atomic, and idiomatic Python
try:
    data = path.read_text()
except FileNotFoundError:
    data = ""
```

The check-then-act version has a genuine race condition: the file can vanish
between the two lines.
""",
    sections={
        "what_is_it": "An exception is an object raised to signal that normal execution "
        "cannot continue. It propagates up the call stack until something handles it, or the "
        "program stops.",
        "why_it_exists": "So that error handling does not have to be threaded through every "
        "return value. A function can report failure without its callers checking a status "
        "code at every level.",
        "how_it_works": "`raise` creates an exception and unwinds the stack, running "
        "`finally` blocks as it goes, until a matching `except` is found. Unhandled "
        "exceptions print a traceback and exit non-zero.",
        "when_to_use": "For conditions the current code cannot sensibly handle: invalid "
        "input, missing resources, failed I/O, broken invariants.",
        "when_not_to_use": "Not for ordinary control flow that is expected to happen "
        "constantly — a `None` return or a sentinel is cheaper and clearer. Not for "
        "validation you can do with a simple conditional at the boundary.",
        "common_mistakes": "Bare `except:`; `except Exception: pass`; catching an exception "
        "you cannot actually recover from; losing the original error by re-raising without "
        "`from`; error messages with no values in them; using exceptions for flow control in "
        "a hot loop.",
        "real_world": "Production systems distinguish *expected* failures (retry the API, "
        "skip the bad row, return 404) from *unexpected* ones (log with full context, alert, "
        "fail the request). Getting that distinction right is most of what 'robust' means.",
        "alternatives": "Return `None` or a sentinel for 'not found'; a Result/Either type "
        "for functional error handling; validation libraries (Pydantic) that collect all "
        "errors at a boundary rather than raising on the first.",
        "performance": "Setting up a `try` block is essentially free in CPython; *raising* "
        "costs roughly a microsecond. Exceptions in a tight loop are a real cost — but "
        "correctness first, and profile before you contort the code.",
        "security": "Never expose a raw traceback to an end user: it leaks file paths, "
        "library versions and sometimes data. Log the detail server-side with a correlation "
        "id, return an opaque message. Never put secrets in an exception message — they end "
        "up in logs.",
    },
    starter_code='''\
def safe_divide(a: float, b: float) -> float | None:
    """Divide a by b, returning None when b is zero."""
    try:
        return a / b
    except ZeroDivisionError:
        print(f"Cannot divide {a} by zero")
        return None


print(safe_divide(10, 2))
print(safe_divide(10, 0))
''',
    examples=(
        Example(
            title="else and finally",
            code="""\
def parse(text):
    try:
        value = int(text)
    except ValueError:
        print(f"  not a number: {text!r}")
        return None
    else:
        print(f"  parsed {value}")
        return value
    finally:
        print("  (finally always runs)")


print("parse('42'):"); parse("42")
print("parse('abc'):"); parse("abc")
""",
            output="parse('42'):\n  parsed 42\n  (finally always runs)\n"
            "parse('abc'):\n  not a number: 'abc'\n  (finally always runs)",
            explanation="`finally` runs even though both paths `return` first. That is what "
            "makes it safe for cleanup.",
        ),
        Example(
            title="Exception chaining preserves the cause",
            code="""\
class ConfigError(Exception):
    \"\"\"Configuration could not be loaded.\"\"\"


def load(raw):
    import json
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("config file is not valid JSON") from exc


try:
    load("{broken")
except ConfigError as exc:
    print(type(exc).__name__, "->", exc)
    print("caused by:", type(exc.__cause__).__name__)
""",
            output="ConfigError -> config file is not valid JSON\ncaused by: JSONDecodeError",
            explanation="The caller gets a domain-level error; the original parsing failure "
            "is still attached as `__cause__` for whoever debugs it.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="exceptions-safe-config",
            title="A configuration loader that fails usefully",
            prompt="""\
Implement `load_setting(config, key, expected_type)`:

* return `config[key]` converted to `expected_type`
* raise `MissingSetting` (a subclass of `ConfigError`) when the key is absent
* raise `InvalidSetting` (also a subclass of `ConfigError`) when the value
  cannot be converted — and chain the original exception with `from`
* both messages must include the key name

`ConfigError`, `MissingSetting` and `InvalidSetting` are yours to define.
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.6,
            estimated_minutes=18,
            xp_reward=45,
            starter_files={
                "main.py": '''\
class ConfigError(Exception):
    """Base class for configuration problems."""


# Define MissingSetting and InvalidSetting here.


def load_setting(config: dict, key: str, expected_type: type):
    """Return config[key] converted to expected_type."""
    ...
'''
            },
            hidden_files={
                "test_config.py": """\
import pytest

from main import ConfigError, InvalidSetting, MissingSetting, load_setting


def test_converts_value():
    assert load_setting({"port": "8080"}, "port", int) == 8080
    assert load_setting({"ratio": "0.5"}, "ratio", float) == 0.5
    assert load_setting({"name": 42}, "name", str) == "42"


def test_missing_key_raises_missing_setting():
    with pytest.raises(MissingSetting) as info:
        load_setting({}, "host", str)
    assert "host" in str(info.value)


def test_bad_value_raises_invalid_setting():
    with pytest.raises(InvalidSetting) as info:
        load_setting({"port": "eighty"}, "port", int)
    assert "port" in str(info.value)


def test_both_are_config_errors():
    assert issubclass(MissingSetting, ConfigError)
    assert issubclass(InvalidSetting, ConfigError)


def test_original_cause_is_preserved():
    with pytest.raises(InvalidSetting) as info:
        load_setting({"port": "eighty"}, "port", int)
    assert isinstance(info.value.__cause__, ValueError), (
        "chain the original error with 'raise ... from exc'"
    )


def test_caller_can_catch_the_base_class():
    with pytest.raises(ConfigError):
        load_setting({}, "anything", str)
"""
            },
            concepts=("exceptions", "custom-exceptions", "classes"),
            hints=(
                HintSpec(
                    "Two failure modes need two different exception classes, but callers "
                    "should be able to catch both with one `except`. What does that imply "
                    "about the class hierarchy?"
                ),
                HintSpec(
                    "A subclass with only a docstring is a complete, valid exception "
                    "class:\n```python\nclass MissingSetting(ConfigError):\n"
                    '    """The key is absent."""\n```'
                ),
                HintSpec(
                    "Conversion failure means `expected_type(value)` raised. Wrap that "
                    "call in try/except and re-raise your own error with `from exc` so "
                    "the original ValueError stays attached as `__cause__`."
                ),
                HintSpec(
                    "```python\nif key not in config:\n"
                    '    raise MissingSetting(f"missing required setting: {key}")\n'
                    "try:\n    return expected_type(config[key])\n"
                    "except (TypeError, ValueError) as exc:\n"
                    '    raise InvalidSetting(f"setting {key} ...") from exc\n```'
                ),
            ),
            solution_files={
                "main.py": '''\
class ConfigError(Exception):
    """Base class for configuration problems.

    Callers that do not care *why* configuration failed catch this; callers that
    want to distinguish a missing key from a bad value catch the subclasses.
    """


class MissingSetting(ConfigError):
    """A required key is absent from the configuration."""


class InvalidSetting(ConfigError):
    """A key is present but its value cannot be used."""


def load_setting(config: dict, key: str, expected_type: type):
    """Return ``config[key]`` converted to ``expected_type``.

    Raises
    ------
    MissingSetting
        If ``key`` is not present.
    InvalidSetting
        If the value cannot be converted; the original conversion error is
        chained as ``__cause__``.
    """
    if key not in config:
        raise MissingSetting(f"missing required setting: {key!r}")

    raw = config[key]
    try:
        return expected_type(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidSetting(
            f"setting {key!r} has value {raw!r}, which is not a valid "
            f"{expected_type.__name__}"
        ) from exc
'''
            },
            solution_explanation="Three points worth keeping. **One base class per subsystem** "
            "lets callers choose their granularity. **`from exc`** keeps the root cause "
            "attached — without it the JSONDecodeError or ValueError that actually explains "
            "the problem is gone. **Messages contain values**: `!r` shows quotes, so an empty "
            "string or a stray space is visible in the log at 3am.",
            misconception_rules=(
                {"pattern": "chain the original error", "misconception": "lost-cause"},
                {"pattern": "issubclass", "misconception": "exception-hierarchy"},
            ),
        ),
        ExerciseSpec(
            slug="exceptions-broad-catch",
            title="Concept check: what does this hide?",
            prompt="""\
```python
def get_user_age(users, name):
    try:
        return int(users[name]["age"])
    except Exception:
        return 0
```

Which statement is the strongest criticism of this function?
""",
            kind=ExerciseKind.QUIZ,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.5,
            estimated_minutes=3,
            xp_reward=15,
            grader=GraderKind.MULTIPLE_CHOICE,
            grader_config={
                "options": [
                    "It is slower than checking with `in` first",
                    "It returns 0 for a genuinely missing user, a malformed record and a "
                    "typo in the code alike — the caller cannot tell a real age of 0 from a "
                    "failure, and a bug in the expression is silently swallowed",
                    "`int()` should be `float()`",
                    "It should use `users.get(name)` instead of `users[name]`",
                ],
                "correct_index": 1,
                "explanation": "The broad `except Exception` catches KeyError, TypeError, "
                "ValueError *and* any AttributeError caused by a typo in the code itself. "
                "Every one becomes the same indistinguishable `0`. Worse, 0 is a plausible "
                "age, so the caller cannot detect the failure. Catch the specific exceptions "
                "you can handle, and return something unambiguous (None, or raise) for the "
                "ones you cannot.",
                "misconception_per_option": {
                    "0": "broad-except",
                    "2": "broad-except",
                    "3": "broad-except",
                },
            },
            concepts=("exceptions", "debugging"),
        ),
    ),
)

CORE_MODULE = ModuleSpec(
    slug="core-python",
    title="Core Python: Functions, Collections and Failure",
    summary="Naming behaviour, choosing data structures deliberately, and handling errors so "
    "that failures are visible rather than silent.",
    level=SkillLevel.INTERMEDIATE,
    lessons=(FUNCTIONS, LISTS, DICTIONARIES, EXCEPTIONS),
)
