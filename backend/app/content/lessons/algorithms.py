"""Module 04: data structures and algorithms.

Six lessons on the collections a learner already half-knows, plus the vocabulary
for defending a choice between them: tuples and unpacking, sets, comprehensions,
sorting with keys, complexity, and the queue and heap types in the standard
library.

The module exists because "which data structure?" is the most common design
decision in Python and the one most often made by habit. Every exercise here is
graded by running real code, and several are graded on whether the structure
chosen is defensible rather than merely correct.
"""

from __future__ import annotations

from app.content.schema import Example, ExerciseSpec, HintSpec, LessonSpec, ModuleSpec
from app.models.enums import ExerciseKind, GraderKind, SkillLevel

# ---------------------------------------------------------------------------
# Lesson 1 — Tuples and unpacking
# ---------------------------------------------------------------------------

TUPLES_AND_UNPACKING = LessonSpec(
    slug="tuples-and-unpacking",
    title="Tuples and Unpacking: Data With a Fixed Shape",
    summary="A tuple says 'this many things, in this order, and it will not change' — and "
    "unpacking is how you read one without index arithmetic.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=28,
    xp_reward=35,
    concepts=("tuples", "mutability"),
    reference_keys=("tuple", "zip", "enumerate"),
    body="""\
## A list and a tuple differ in intent, not just in mutability

Everyone learns "a tuple is an immutable list". That is true and it is the least
interesting part. The useful distinction is what each one *says* to the next
reader:

```python
scores = [88, 91, 79]          # a list: an unknown number of the same kind of thing
point  = (3.5, -1.0)           # a tuple: exactly two things, and position means something
```

`scores[0]` is "some score". `point[0]` is "the x coordinate" — position carries
meaning. That is why a tuple of mixed types is normal and a list of mixed types
is usually a smell.

Rule of thumb: if you would be comfortable calling `.append()` on it, it wants to
be a list. If appending would make it a different kind of thing, it wants to be a
tuple.

## Unpacking replaces index arithmetic

Reading a tuple by index is how you get bugs that survive review:

```python
x = point[0]
y = point[1]
```

Nothing there catches the day `point` grows a z coordinate. Unpacking does:

```python
x, y = point            # ValueError the moment the shape changes
```

That is a feature. A loud failure at the assignment beats a silent wrong answer
three functions later.

Starred unpacking handles "the first, and the rest":

```python
first, *rest = [10, 20, 30, 40]     # first=10, rest=[20, 30, 40]
*body, last = [10, 20, 30, 40]      # body=[10, 20, 30], last=40
```

Note `rest` is a **list**, even when the source was a tuple. The star collects
into a list because its length is not known in advance.

## Swapping, and why it works

```python
a, b = b, a
```

The right-hand side is evaluated *first*, building a tuple `(b, a)`, and only
then is it unpacked into the names on the left. No temporary variable, and no
order-of-assignment bug.

## Tuples are only as immutable as their contents

This is the trap:

```python
row = (1, [2, 3])
row[1].append(4)        # fine — the tuple still holds the same list object
row[1] = [9]            # TypeError — you cannot rebind a slot
```

Immutability is about the *slots*, not the objects in them. It follows that a
tuple is hashable only when everything inside it is:

```python
{(1, 2): "ok"}          # fine
{(1, [2]): "no"}        # TypeError: unhashable type: 'list'
```

That is exactly why `(date, region)` works as a dictionary key and makes tuples
the natural type for a compound key.

## zip and enumerate produce tuples, and that is why they read well

```python
for index, name in enumerate(names, start=1):
    ...
for name, score in zip(names, scores, strict=True):
    ...
```

Both yield tuples, and unpacking in the `for` target names the parts. Pass
`strict=True` to `zip` when the inputs *should* be the same length — without it,
`zip` silently stops at the shortest, which is a data-loss bug that produces no
error at all.
""",
    sections={
        "what_is_it": "A tuple is an immutable, ordered sequence. Its length and the meaning "
        "of each position are fixed when it is created, and unpacking assigns those positions "
        "to names in one statement.",
        "why_it_exists": "Some data has a shape rather than a count — a coordinate, a database "
        "row, a function returning two things. A type that cannot grow lets both the reader "
        "and the interpreter rely on that shape, and makes the value hashable so it can be a "
        "dict key or a set member.",
        "how_it_works": "A tuple stores a fixed array of references. Immutability applies to "
        "those references, not to the objects they point at, so a tuple containing a list is "
        "still mutable through that list. Unpacking evaluates the right-hand side completely, "
        "then binds positionally, raising ValueError on any length mismatch.",
        "when_to_use": "Fixed-shape records, multiple return values, compound dictionary keys "
        "and set members, and any sequence whose length is part of its meaning.",
        "when_not_to_use": "A homogeneous collection that grows or shrinks — that is a list. "
        "And once a tuple has more than three positions, positional meaning stops being "
        "readable: `row[4]` tells the reader nothing. Reach for a NamedTuple or a dataclass, "
        "which keep the fixed shape and add names.",
        "common_mistakes": "Writing `(x)` and expecting a tuple — it is just x in parentheses; "
        "the comma makes a tuple, so it is `(x,)`. Assuming a tuple of lists is hashable. "
        "Using zip without strict=True on inputs that must match, and silently dropping the "
        "tail of the longer one.",
        "real_world": "Database drivers return rows as tuples. `os.path.splitext` returns "
        "(root, ext). Dictionary keys in reporting code are almost always tuples like "
        "(region, month). `sys.version_info` is a tuple so that version comparisons work.",
        "alternatives": "collections.namedtuple or typing.NamedTuple for a fixed shape with "
        "names and no extra cost; a frozen dataclass when you also want methods, defaults and "
        "validation; a dict when the keys are genuinely dynamic.",
        "performance": "A tuple is slightly smaller and faster to build than the equivalent "
        "list, because its size is known at creation. That difference almost never justifies "
        "choosing one over the other — pick on meaning, not on speed. Where it does matter is "
        "hashing: a tuple key lets a dict do O(1) lookup on a compound value.",
        "security": "Immutability is a useful defence for shared constants: a module-level "
        "tuple cannot be mutated by a caller the way a list can. It is not a security "
        "boundary — a tuple of mutable objects is still mutable through them.",
    },
    starter_code="""\
point = (3.5, -1.0)
x, y = point
print(f"x={x} y={y}")

first, *rest = [10, 20, 30, 40]
print(first, rest)
""",
    examples=(
        Example(
            title="Unpacking names the positions",
            code='row = ("2026-01-15", "EMEA", 4200)\ndate, region, revenue = row\n'
            'print(f"{region} made {revenue} on {date}")',
            output="EMEA made 4200 on 2026-01-15",
            explanation="Compare with `row[1]` and `row[2]` at the point of use. The names "
            "are the documentation, and they cost one line.",
        ),
        Example(
            title="A length mismatch fails loudly",
            code='date, region = ("2026-01-15", "EMEA", 4200)',
            output="ValueError: too many values to unpack (expected 2)",
            explanation="This is the behaviour you want. Reading by index would have "
            "silently ignored the third field.",
        ),
        Example(
            title="One comma is the difference",
            code="print(type((5)))\nprint(type((5,)))",
            output="<class 'int'>\n<class 'tuple'>",
            explanation="Parentheses group; the comma builds the tuple. This bites when a "
            "single-element tuple is meant — a common bug in test parameter lists.",
        ),
        Example(
            title="Immutable slots, mutable contents",
            code="row = (1, [2, 3])\nrow[1].append(4)\nprint(row)",
            output="(1, [2, 3, 4])",
            explanation="The tuple never changed — it still references the same list. The "
            "list changed. This is why such a tuple cannot be hashed.",
        ),
    ),
    visualizations=(
        {
            "kind": "comparison",
            "title": "List or tuple?",
            "rows": [
                {"question": "Does the length carry meaning?", "list": "no", "tuple": "yes"},
                {"question": "Would .append() make sense?", "list": "yes", "tuple": "no"},
                {"question": "Can it be a dict key?", "list": "no", "tuple": "if contents are"},
                {"question": "Mixed types normal?", "list": "rarely", "tuple": "often"},
            ],
        },
    ),
    exercises=(
        ExerciseSpec(
            slug="tuples-parse-record",
            title="Return a fixed-shape record",
            prompt="Write `parse_record(line)` which takes a string like\n\n"
            "```\n2026-01-15,EMEA,4200\n```\n\n"
            "and returns a **tuple** `(date, region, revenue)` where `date` and `region` are "
            "strings and `revenue` is an `int`.\n\n"
            "Surrounding whitespace on any field must be stripped. Raise `ValueError` with "
            "the message `expected 3 fields` if the line does not have exactly three fields.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.35,
            estimated_minutes=14,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def parse_record(line: str) -> tuple[str, str, int]:
    """Parse "date,region,revenue" into a fixed-shape tuple."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_record.py": """\
import pytest

from main import parse_record


def test_returns_a_tuple():
    result = parse_record("2026-01-15,EMEA,4200")
    assert isinstance(result, tuple), "return a tuple, not a list or a dict"
    assert result == ("2026-01-15", "EMEA", 4200)


def test_revenue_is_an_int():
    _, _, revenue = parse_record("2026-01-15,EMEA,4200")
    assert isinstance(revenue, int), "revenue must be converted from text to int"


def test_strips_whitespace():
    assert parse_record("  2026-01-15 , EMEA ,  4200 ") == ("2026-01-15", "EMEA", 4200)


def test_wrong_field_count_raises():
    with pytest.raises(ValueError, match="expected 3 fields"):
        parse_record("2026-01-15,EMEA")


def test_too_many_fields_also_raises():
    with pytest.raises(ValueError, match="expected 3 fields"):
        parse_record("a,b,c,d")
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("tuples",),
            hints=(
                HintSpec('`line.split(",")` gives you the fields as a list.'),
                HintSpec(
                    "Check `len(fields)` before unpacking, so you can raise your own error "
                    "rather than letting ValueError escape with a different message."
                ),
                HintSpec(
                    "`str.strip()` removes surrounding whitespace. You need it on every "
                    "field, not just the first."
                ),
                HintSpec(
                    "Shape: split, check the length, then "
                    "`date, region, revenue = (f.strip() for f in fields)` — and convert "
                    "revenue with `int(...)` before returning the tuple."
                ),
            ),
            solution_files={
                "main.py": '''\
def parse_record(line: str) -> tuple[str, str, int]:
    """Parse "date,region,revenue" into a fixed-shape tuple."""
    fields = line.split(",")
    if len(fields) != 3:
        raise ValueError("expected 3 fields")
    date, region, revenue = (field.strip() for field in fields)
    return (date, region, int(revenue))
'''
            },
            solution_explanation="The length check comes before unpacking so the error "
            "message is ours rather than Python's. Stripping every field in one generator "
            "expression avoids three near-identical lines, and the int conversion happens at "
            "the boundary — once, here, rather than at every use site.",
            misconception_rules=(
                {"pattern": "test_returns_a_tuple", "misconception": "list-vs-tuple"},
                {"pattern": "test_revenue_is_an_int", "misconception": "type-mismatch"},
            ),
        ),
        ExerciseSpec(
            slug="tuples-zip-totals",
            title="Pair two sequences safely",
            prompt="Write `pair_totals(names, amounts)` returning a list of "
            "`(name, amount)` tuples.\n\n"
            "The two inputs must be the same length: if they are not, raise `ValueError`. "
            "Do not silently ignore extra items — that is the bug this exercise is about.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.4,
            estimated_minutes=14,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def pair_totals(names: list[str], amounts: list[int]) -> list[tuple[str, int]]:
    """Zip names with amounts, refusing mismatched lengths."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_pairs.py": """\
import pytest

from main import pair_totals


def test_pairs_in_order():
    assert pair_totals(["a", "b"], [1, 2]) == [("a", 1), ("b", 2)]


def test_elements_are_tuples():
    first = pair_totals(["a"], [1])[0]
    assert isinstance(first, tuple), "each pair must be a tuple"


def test_empty_inputs():
    assert pair_totals([], []) == []


def test_longer_names_raises():
    with pytest.raises(ValueError):
        pair_totals(["a", "b", "c"], [1, 2])


def test_longer_amounts_raises():
    with pytest.raises(ValueError):
        pair_totals(["a"], [1, 2])
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("tuples",),
            hints=(
                HintSpec(
                    "`zip` stops at the shorter input by default — which is exactly the "
                    "silent behaviour the prompt forbids."
                ),
                HintSpec(
                    "Since Python 3.10 `zip` takes `strict=True`, which raises ValueError on "
                    "a length mismatch."
                ),
                HintSpec(
                    "`list(...)` around the zip turns the iterator into the list the tests "
                    "compare against."
                ),
                HintSpec("One line: `return list(zip(names, amounts, strict=True))`."),
            ),
            solution_files={
                "main.py": '''\
def pair_totals(names: list[str], amounts: list[int]) -> list[tuple[str, int]]:
    """Zip names with amounts, refusing mismatched lengths."""
    return list(zip(names, amounts, strict=True))
'''
            },
            solution_explanation="`strict=True` is the whole exercise. An explicit length "
            "check first would also pass, but this states the requirement where the pairing "
            "happens instead of somewhere a later edit can drift away from.",
        ),
        ExerciseSpec(
            slug="tuples-swap-debug",
            title="Debug: the rotation loses a value",
            prompt="`rotate_left(values)` should move the first element to the end: "
            "`[1, 2, 3]` becomes `[2, 3, 1]`.\n\n"
            "It currently returns the wrong result. The bug is a classic one — a value is "
            "overwritten before it is read. Fix it without adding an `if`.",
            kind=ExerciseKind.DEBUG,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.45,
            estimated_minutes=16,
            xp_reward=40,
            starter_files={
                "main.py": '''\
def rotate_left(values: list[int]) -> list[int]:
    """Move the first element to the end, returning a new list."""
    result = list(values)
    for index in range(len(result) - 1):
        result[index] = result[index + 1]
        result[index + 1] = result[index]
    return result
'''
            },
            hidden_files={
                "test_rotate.py": """\
from main import rotate_left


def test_three_elements():
    assert rotate_left([1, 2, 3]) == [2, 3, 1]


def test_two_elements():
    assert rotate_left([1, 2]) == [2, 1]


def test_single_element():
    assert rotate_left([9]) == [9]


def test_empty():
    assert rotate_left([]) == []


def test_does_not_mutate_the_input():
    original = [1, 2, 3]
    rotate_left(original)
    assert original == [1, 2, 3], "return a new list; do not modify the caller's list"


def test_longer_sequence():
    assert rotate_left([1, 2, 3, 4, 5]) == [2, 3, 4, 5, 1]
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("tuples", "mutability"),
            hints=(
                HintSpec(
                    "Trace the loop by hand with [1, 2, 3]. Write down result after every "
                    "single assignment, not after every iteration."
                ),
                HintSpec(
                    "The second line of the loop reads `result[index]` — but the first line "
                    "just overwrote it. The original value is already gone."
                ),
                HintSpec(
                    "Python can assign two names at once from a tuple, evaluating the whole "
                    "right-hand side before binding anything: `a, b = b, a`."
                ),
                HintSpec(
                    "You do not need the loop at all. Slicing gives it directly: "
                    "everything from index 1 onwards, followed by the first element."
                ),
            ),
            solution_files={
                "main.py": '''\
def rotate_left(values: list[int]) -> list[int]:
    """Move the first element to the end, returning a new list."""
    return list(values[1:]) + list(values[:1])
'''
            },
            solution_explanation="The original loop destroyed `result[index]` before copying "
            "it, so every element became the next one. A swap (`a, b = b, a`) would fix the "
            "immediate bug, but the slice states the intent in one line and handles the empty "
            "and single-element cases without a special case: `values[:1]` is `[]` for an "
            "empty list, where `values[0]` would raise.",
            misconception_rules=(
                {"pattern": "test_does_not_mutate_the_input", "misconception": "aliasing"},
                {"pattern": "test_empty", "misconception": "off-by-one"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 2 — Sets
# ---------------------------------------------------------------------------

SETS_AND_MEMBERSHIP = LessonSpec(
    slug="sets-and-membership",
    title="Sets: Membership, Deduplication and Set Algebra",
    summary="When the question is 'is it in there?' or 'what is in both?', a set turns a "
    "loop into an operator and O(n) into O(1).",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=28,
    xp_reward=35,
    concepts=("sets", "complexity"),
    reference_keys=("set", "frozenset"),
    body="""\
## The one-line version

A set is an unordered collection of unique, hashable items. It answers two
questions much better than a list does: *is this in there?* and *how do these two
collections relate?*

```python
seen = {"ada", "grace"}
"ada" in seen          # True, and it did not scan
```

## Why membership is the headline

`in` on a list compares against each element in turn. `in` on a set hashes the
value and looks in one place:

```python
names_list = [f"user{i}" for i in range(100_000)]
names_set  = set(names_list)

"user99999" in names_list   # ~100,000 comparisons
"user99999" in names_set    # one hash, one bucket
```

This is the single most valuable thing in this lesson, because the mistake it
prevents is so common:

```python
# O(n * m) — a scan of `banned` for every user
flagged = [u for u in users if u in banned_list]

# O(n) — hash lookup for every user
banned = set(banned_list)
flagged = [u for u in users if u in banned]
```

On 10,000 users against 10,000 banned names, that is a hundred million
comparisons versus ten thousand hashes. Same output, same readability, three
orders of magnitude.

## Set algebra replaces loops with intent

```python
a = {1, 2, 3}
b = {3, 4}

a | b        # union         {1, 2, 3, 4}   — in either
a & b        # intersection  {3}            — in both
a - b        # difference    {1, 2}         — in a, not in b
a ^ b        # symmetric     {1, 2, 4}      — in exactly one
a <= b       # subset?       False
```

"Which permissions is this user missing?" is `required - granted`. Written as a
loop it is five lines and a comment; written as a difference it needs neither.

## Sets are unordered, and that is a real constraint

There is no `set[0]`, and iteration order is an implementation detail you must
not rely on. So deduplicating *while preserving order* is not a job for a set
alone:

```python
# loses the order
unique = list(set(items))

# keeps it: dict keys are unique and, since 3.7, ordered by insertion
unique = list(dict.fromkeys(items))
```

That second line is worth memorising.

## Only hashable things can go in

```python
{[1, 2]}                 # TypeError: unhashable type: 'list'
{(1, 2)}                 # fine
```

Same rule as dictionary keys, and the same reason: the container needs a stable
hash. This is why a set of tuples is idiomatic and a set of lists is impossible —
and why `frozenset` exists, for when you need a set that can itself be a key.

## Mutating versus deriving

```python
s.add(4)                 # in place, returns None
s.discard(9)             # in place, no error if absent
s.remove(9)              # in place, KeyError if absent
t = s | {4}              # new set, s untouched
```

`discard` versus `remove` is a genuine API choice, not a redundancy: use `remove`
when absence is a bug you want to hear about.
""",
    sections={
        "what_is_it": "A set is a mutable, unordered collection of unique hashable objects, "
        "supporting O(1) membership tests and the mathematical set operations as operators.",
        "why_it_exists": "Two problems recur constantly — uniqueness and membership — and both "
        "are quadratic or worse when solved with lists. A hash-based container makes them "
        "linear and constant respectively, and lets relationships between collections be "
        "written as operators rather than nested loops.",
        "how_it_works": "Items are stored by hash in a table. Membership hashes the value and "
        "inspects one bucket, so cost does not grow with size. Uniqueness is a consequence: "
        "two equal objects hash the same and occupy the same slot. Because position is decided "
        "by hash, order is not meaningful and must not be relied on.",
        "when_to_use": "Membership tests, especially inside a loop; deduplication where order "
        "does not matter; and any question phrased as 'in both', 'in either', 'in one but not "
        "the other', or 'is this a subset of that'.",
        "when_not_to_use": "When order matters, when duplicates are data (a set silently "
        "discards them — if counts matter, use collections.Counter), when items are unhashable, "
        "or when you need indexing or slicing.",
        "common_mistakes": "Writing `{}` for an empty set — that is a dict; use `set()`. "
        "Assuming iteration order is stable. Using `list(set(x))` to dedupe when order matters. "
        "Calling `.add()` and expecting a new set back: it returns None, so `s = s.add(1)` "
        "destroys the set.",
        "real_world": "Permission checks (`required - granted` gives what is missing), "
        "deduplicating IDs from a paginated API, finding which files changed between two "
        "directory listings, and tracking visited nodes in a crawler so it terminates.",
        "alternatives": "dict.fromkeys for order-preserving dedup; collections.Counter when "
        "duplicate counts matter; frozenset when the set must be hashable; a sorted list with "
        "bisect when you need both membership and order.",
        "performance": "Membership, add and discard are O(1) on average. Union, intersection "
        "and difference are linear in the size of the inputs. The trade is memory and hashing "
        "cost: building a set is O(n), so it pays off when you test membership more than a "
        "couple of times — not for a single lookup in a five-item list.",
        "security": "Sets are the right structure for allowlists and denylists, because the "
        "check is a single unambiguous operation rather than a loop someone can get subtly "
        "wrong. Never build one from untrusted input without bounding its size: an attacker "
        "who controls the number of distinct values controls your memory use.",
    },
    starter_code="""\
required = {"read", "write", "deploy"}
granted = {"read", "write"}

print("missing:", required - granted)
print("has read?", "read" in granted)
print("dedup, order kept:", list(dict.fromkeys([3, 1, 3, 2, 1])))
""",
    examples=(
        Example(
            title="Set algebra says what a loop only implies",
            code='required = {"read", "write", "deploy"}\ngranted = {"read", "write"}\n'
            "print(sorted(required - granted))",
            output="['deploy']",
            explanation="`sorted` is there only to make the output deterministic for "
            "printing — the set itself has no order.",
        ),
        Example(
            title="Deduplicating loses order; dict.fromkeys does not",
            code="items = [3, 1, 3, 2, 1]\nprint(sorted(set(items)))\n"
            "print(list(dict.fromkeys(items)))",
            output="[1, 2, 3]\n[3, 1, 2]",
            explanation="The second keeps first-seen order: 3 came first in the input. Note "
            "the first line needed `sorted` to print predictably at all.",
        ),
        Example(
            title="The empty-set trap",
            code="print(type({}))\nprint(type(set()))",
            output="<class 'dict'>\n<class 'set'>",
            explanation="`{}` was a dict long before set literals existed, so the braces "
            "were already taken. There is no empty set literal.",
        ),
        Example(
            title="add returns None",
            code="s = {1, 2}\nresult = s.add(3)\nprint(s, result)",
            output="{1, 2, 3} None",
            explanation="The set was modified in place. Assigning the return value is how "
            "people accidentally replace a set with None.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="sets-missing-permissions",
            title="Report missing permissions",
            prompt="Write `missing_permissions(required, granted)` returning a **sorted list** "
            "of the permissions in `required` that are not in `granted`.\n\n"
            "Both inputs are iterables of strings and may contain duplicates. The result must "
            "be sorted alphabetically and contain no duplicates.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.35,
            estimated_minutes=13,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def missing_permissions(required, granted) -> list[str]:
    """Which required permissions have not been granted?"""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_permissions.py": """\
from main import missing_permissions


def test_finds_the_gap():
    assert missing_permissions(["read", "write", "deploy"], ["read"]) == ["deploy", "write"]


def test_result_is_sorted():
    result = missing_permissions(["z", "a", "m"], [])
    assert result == sorted(result) == ["a", "m", "z"]


def test_nothing_missing():
    assert missing_permissions(["read"], ["read", "write"]) == []


def test_duplicates_collapse():
    assert missing_permissions(["read", "read", "write"], []) == ["read", "write"]


def test_accepts_any_iterable():
    assert missing_permissions({"read"}, iter(["write"])) == ["read"]


def test_returns_a_list():
    assert isinstance(missing_permissions(["a"], []), list), "return a list, not a set"
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("sets",),
            hints=(
                HintSpec("The question 'in required but not in granted' is a set difference."),
                HintSpec(
                    "The `-` operator needs sets on both sides. `set(...)` converts any "
                    "iterable, which also handles the duplicates for you."
                ),
                HintSpec(
                    "A set has no order, so the difference must be sorted before returning — "
                    "and `sorted()` conveniently returns a list."
                ),
                HintSpec("One line: `return sorted(set(required) - set(granted))`."),
            ),
            solution_files={
                "main.py": '''\
def missing_permissions(required, granted) -> list[str]:
    """Which required permissions have not been granted?"""
    return sorted(set(required) - set(granted))
'''
            },
            solution_explanation="Converting both to sets handles duplicates and accepts any "
            "iterable, including a one-shot iterator. `sorted` does double duty: it makes the "
            "output deterministic and produces the list the contract asks for.",
        ),
        ExerciseSpec(
            slug="sets-dedup-keep-order",
            title="Deduplicate without losing order",
            prompt="Write `dedupe(items)` returning a list with duplicates removed and the "
            "**first occurrence order preserved**.\n\n"
            "`[3, 1, 3, 2, 1]` becomes `[3, 1, 2]`.\n\n"
            "`list(set(items))` will fail these tests, and that is the point.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.4,
            estimated_minutes=14,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def dedupe(items: list) -> list:
    """Remove duplicates, keeping first-seen order."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_dedupe.py": """\
from main import dedupe


def test_keeps_first_seen_order():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_already_unique_is_unchanged():
    assert dedupe([1, 2, 3]) == [1, 2, 3]


def test_empty():
    assert dedupe([]) == []


def test_strings():
    assert dedupe(["b", "a", "b", "c"]) == ["b", "a", "c"]


def test_all_identical():
    assert dedupe([7, 7, 7]) == [7]


def test_order_is_not_sorted_order():
    # A solution that sorts would pass some of the tests above but not this one.
    assert dedupe([5, 9, 1, 9]) == [5, 9, 1]


def test_does_not_mutate_the_input():
    original = [1, 1, 2]
    dedupe(original)
    assert original == [1, 1, 2], "do not modify the caller's list"
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("sets", "dictionaries"),
            hints=(
                HintSpec(
                    "A set gives you uniqueness but throws order away. You need something "
                    "that provides both."
                ),
                HintSpec(
                    "One approach: keep a `seen` set for the fast membership test, and append "
                    "to a result list only when the item is new."
                ),
                HintSpec(
                    "There is also a one-liner. Dictionary keys are unique *and*, since "
                    "Python 3.7, keep insertion order."
                ),
                HintSpec(
                    "`list(dict.fromkeys(items))` builds a dict whose keys are the items in "
                    "first-seen order, then takes those keys as a list."
                ),
            ),
            solution_files={
                "main.py": '''\
def dedupe(items: list) -> list:
    """Remove duplicates, keeping first-seen order."""
    return list(dict.fromkeys(items))
'''
            },
            solution_explanation="`dict.fromkeys` inserts each item as a key; duplicates "
            "collapse because keys are unique, and insertion order is preserved because "
            "dicts are ordered. The explicit `seen` set version is equally correct and more "
            "obvious to a reader who does not know this idiom — either is defensible, but "
            "both must be O(n), which a repeated `if item not in result` on a list is not.",
            misconception_rules=(
                {"pattern": "test_keeps_first_seen_order", "misconception": "set-loses-order"},
                {"pattern": "test_order_is_not_sorted_order", "misconception": "set-loses-order"},
            ),
        ),
        ExerciseSpec(
            slug="sets-membership-cost",
            title="Which lookup scales?",
            prompt="`banned` holds 50,000 names and `users` holds 50,000 names.\n\n"
            "```python\nflagged = [u for u in users if u in banned]\n```\n\n"
            "Which statement is correct?",
            kind=ExerciseKind.QUIZ,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.4,
            estimated_minutes=6,
            xp_reward=20,
            grader=GraderKind.MULTIPLE_CHOICE,
            grader_config={
                "options": [
                    "It is O(n) either way — the comprehension visits each user once.",
                    "If banned is a list this is O(n*m); making banned a set makes it O(n).",
                    "Converting banned to a set makes it slower, because building the set "
                    "costs O(n) first.",
                    "Sets and lists have the same membership cost; only insertion differs.",
                ],
                "correct_index": 1,
            },
            concepts=("sets", "complexity"),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 3 — Comprehensions
# ---------------------------------------------------------------------------

COMPREHENSIONS_IN_DEPTH = LessonSpec(
    slug="comprehensions-in-depth",
    title="Comprehensions: Describing a Collection Instead of Building One",
    summary="A comprehension states what the result *is*, rather than the steps that "
    "accumulate it — and stops being a good idea at exactly the point it stops fitting on "
    "one line.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=30,
    xp_reward=40,
    concepts=("comprehensions", "lists"),
    reference_keys=("sorted", "zip"),
    body="""\
## The shape

```python
squares = [n * n for n in range(5)]                 # [0, 1, 4, 9, 16]
evens   = [n for n in range(10) if n % 2 == 0]      # [0, 2, 4, 6, 8]
```

Read it as: *the list of `expression`, for each `item` in `iterable`, where
`condition`*. The imperative equivalent is three lines and a mutable accumulator:

```python
squares = []
for n in range(5):
    squares.append(n * n)
```

The comprehension is not shorter for its own sake. It is shorter because it
removes the accumulator — and the accumulator is where the bugs live: forgetting
to initialise it, appending in the wrong branch, reusing it in a nested loop.

## All four flavours

```python
[n * n for n in xs]              # list
{n * n for n in xs}              # set    — deduplicates
{k: v for k, v in pairs}         # dict
(n * n for n in xs)              # generator — lazy, no list built
```

The last one matters for memory. `sum(n * n for n in range(10_000_000))` never
builds a ten-million-element list; the list version does, and may not fit.

## Filtering and transforming are different positions

```python
[transform(n) for n in xs if keep(n)]
#  ^ what comes out          ^ which ones get considered
```

A conditional *expression* goes in the transform slot instead, and does not
filter — it changes what is produced:

```python
["even" if n % 2 == 0 else "odd" for n in xs]     # same length as xs
[n for n in xs if n % 2 == 0]                     # shorter than xs
```

Confusing these two is the most common comprehension bug. If your result must be
the same length as the input, you want the `if/else` in the front. If it must be
shorter, you want the trailing `if`.

## Nesting reads left to right, which surprises people

```python
[cell for row in grid for cell in row]      # flatten
```

The loops appear in the same order you would write them nested — outer first.
The temptation is to read it inside-out; do not.

Two levels is the practical limit. Beyond that, a reader has to simulate the
thing to know what it produces, and the comprehension has stopped earning its
keep.

## Where comprehensions stop being right

They are expressions, so they cannot contain a statement — no `try`, no `break`,
no logging in the middle. Do not fight that. When you need any of those, or when
the line no longer fits comfortably, write the loop:

```python
# Bad: correct, and nobody can read it
result = [f(x) for xs in groups for x in xs if x and f(x) > threshold and x not in seen]

# Better: the loop can breathe, and can log or break
result = []
for xs in groups:
    for x in xs:
        if not x or x in seen:
            continue
        value = f(x)              # computed once, not twice
        if value > threshold:
            result.append(value)
```

Note what the loop fixed beyond readability: the comprehension called `f(x)`
twice, once in the filter and once in the transform.

## The walrus, for when you need the value you filtered on

```python
result = [value for x in xs if (value := f(x)) > threshold]
```

This computes `f(x)` once and keeps the comprehension. Use it when it genuinely
simplifies; it is not an excuse to push a comprehension past two lines.
""",
    sections={
        "what_is_it": "A comprehension is an expression that builds a list, set, dict or "
        "generator by describing its contents — a transform, a source iterable, and an "
        "optional filter — rather than by accumulating into a variable.",
        "why_it_exists": "Building a collection element by element requires a mutable "
        "accumulator, and that accumulator is a source of defects and of noise. A "
        "comprehension makes the result a single expression, so it can be assigned, passed or "
        "returned directly, and cannot be half-built.",
        "how_it_works": "Python compiles the comprehension to its own scope with an implicit "
        "accumulator, so the loop variable does not leak into the enclosing function. Clauses "
        "are evaluated left to right — outer loop first for nested comprehensions — and the "
        "filter runs before the transform. A generator expression yields lazily instead of "
        "building the whole result.",
        "when_to_use": "A single transform, an optional filter, one or at most two levels of "
        "iteration, and a line that still reads as one thought.",
        "when_not_to_use": "When you need a statement inside — try/except, break, continue, "
        "logging. When there are three or more clauses. When the same expensive call appears "
        "in both the filter and the transform. And when you are using it purely for its side "
        "effects: a comprehension whose result you discard should be a for loop.",
        "common_mistakes": "Confusing the trailing filter (changes length) with a leading "
        "if/else conditional expression (preserves length). Calling an expensive function "
        "twice, once to filter and once to transform. Reading nested comprehensions "
        "inside-out. Building a huge list where a generator expression would do.",
        "real_world": "Extracting one field from a list of API records; building a lookup dict "
        "from a query result; filtering paths by extension; converting rows to typed objects "
        "at a data boundary. In review, a nested comprehension is a routine thing to ask "
        "someone to unroll.",
        "alternatives": "An explicit for loop when statements or logging are needed; map and "
        "filter when you already have the function and no lambda is required; a generator "
        "expression when the result is consumed once; itertools for chaining and grouping.",
        "performance": "A list comprehension is measurably faster than an equivalent append "
        "loop, because the accumulation happens in the interpreter rather than through a "
        "method call per item. A generator expression trades that for constant memory and is "
        "the right default when the result is consumed once and never indexed.",
        "security": "Nothing about a comprehension is unsafe in itself, but its density hides "
        "things in review — an unvalidated field, a missing bound. Code that filters "
        "untrusted input is exactly the code most worth writing as an explicit, readable loop.",
    },
    starter_code="""\
words = ["alpha", "be", "gamma", "hi"]

lengths = {w: len(w) for w in words}
long_words = [w.upper() for w in words if len(w) > 2]
labels = ["long" if len(w) > 2 else "short" for w in words]

print(lengths)
print(long_words)
print(labels)
""",
    examples=(
        Example(
            title="Filter shortens; a conditional expression does not",
            code="xs = [1, 2, 3, 4]\nprint([n for n in xs if n % 2 == 0])\n"
            'print(["even" if n % 2 == 0 else "odd" for n in xs])',
            output="[2, 4]\n['odd', 'even', 'odd', 'even']",
            explanation="Same data, two different questions. The first asks *which*; the "
            "second asks *what to call each one*. Mixing them up is the classic bug.",
        ),
        Example(
            title="A dict comprehension builds a lookup in one step",
            code='rows = [("EMEA", 4200), ("APAC", 3100)]\n'
            "print({region: revenue for region, revenue in rows})",
            output="{'EMEA': 4200, 'APAC': 3100}",
            explanation="Unpacking in the `for` target names the parts, so the body reads "
            "as the mapping it produces.",
        ),
        Example(
            title="Nesting reads outer loop first",
            code="grid = [[1, 2], [3, 4]]\nprint([cell for row in grid for cell in row])",
            output="[1, 2, 3, 4]",
            explanation="Same order as the nested loops you would otherwise write. Reading "
            "it right-to-left gives the wrong answer.",
        ),
        Example(
            title="The loop variable does not leak",
            code="n = 'untouched'\nsquares = [n * n for n in range(3)]\nprint(squares, n)",
            output="[0, 1, 4] untouched",
            explanation="The comprehension has its own scope. The equivalent for loop would "
            "have overwritten `n` — a real difference, not a detail.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="comp-index-by-key",
            title="Build a lookup from records",
            prompt="Write `index_by_id(records)` which takes a list of dicts, each with an "
            '`"id"` key, and returns a dict mapping each id to its whole record.\n\n'
            "Use a dict comprehension. If two records share an id, the **last** one wins.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.35,
            estimated_minutes=13,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def index_by_id(records: list[dict]) -> dict:
    """Map each record's "id" to the record itself."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_index.py": """\
from main import index_by_id


def test_indexes_by_id():
    records = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    assert index_by_id(records) == {1: {"id": 1, "name": "a"}, 2: {"id": 2, "name": "b"}}


def test_empty():
    assert index_by_id([]) == {}


def test_last_duplicate_wins():
    records = [{"id": 1, "name": "first"}, {"id": 1, "name": "second"}]
    assert index_by_id(records)[1]["name"] == "second"


def test_values_are_the_records_themselves():
    record = {"id": 7, "name": "x"}
    assert index_by_id([record])[7] is record, "map to the record object, not a copy"


def test_string_ids_work_too():
    assert index_by_id([{"id": "a7"}]) == {"a7": {"id": "a7"}}
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("comprehensions", "dictionaries"),
            hints=(
                HintSpec(
                    "A dict comprehension has the shape "
                    "`{key_expression: value_expression for item in iterable}`."
                ),
                HintSpec('The key comes from inside each record: `record["id"]`.'),
                HintSpec("The value is the record itself — not a copy, and not one of its fields."),
                HintSpec(
                    '`return {record["id"]: record for record in records}`. Later keys '
                    "overwrite earlier ones, which is exactly the 'last one wins' rule."
                ),
            ),
            solution_files={
                "main.py": '''\
def index_by_id(records: list[dict]) -> dict:
    """Map each record's "id" to the record itself."""
    return {record["id"]: record for record in records}
'''
            },
            solution_explanation="Duplicate handling is free: a dict comprehension assigns "
            "keys in iteration order, so a repeated id is simply overwritten by the later "
            "record. Note the values are the same objects, not copies — `is` in the test "
            "pins that down, because a `dict(record)` copy would break callers who expect "
            "to mutate through the index.",
        ),
        ExerciseSpec(
            slug="comp-refactor-loop",
            title="Refactor: replace the accumulator",
            prompt="`clean_names` works, but it builds its result with an accumulator and a "
            "`for` loop. Rewrite it as a **single list comprehension**.\n\n"
            "Behaviour must not change: strip each name, drop the ones that are empty after "
            "stripping, and title-case the rest.\n\n"
            "The grader checks the structure of your code, not just its output: it requires a "
            "list comprehension and forbids a `for` statement.",
            kind=ExerciseKind.REFACTOR,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.45,
            estimated_minutes=15,
            xp_reward=40,
            starter_files={
                "main.py": '''\
def clean_names(raw: list[str]) -> list[str]:
    """Strip, drop blanks, and title-case."""
    result = []
    for name in raw:
        stripped = name.strip()
        if stripped:
            result.append(stripped.title())
    return result
'''
            },
            grader=GraderKind.STATIC_ASSERT,
            grader_config={
                "target_file": "main.py",
                "assertions": [
                    {
                        "kind": "defines_function",
                        "name": "clean_names",
                        "label": "Still defines clean_names()",
                    },
                    {
                        "kind": "uses_construct",
                        "node": "ListComp",
                        "label": "Uses a list comprehension",
                    },
                    {
                        "kind": "forbids_construct",
                        "node": "For",
                        "message": "Replace the for statement with the comprehension",
                    },
                    {"kind": "max_lines", "value": 6},
                ],
            },
            concepts=("comprehensions",),
            hints=(
                HintSpec(
                    "The `if stripped:` test becomes the comprehension's trailing filter, "
                    "because it changes how many items come out."
                ),
                HintSpec("`.title()` is the transform — it goes at the front, before the `for`."),
                HintSpec(
                    "The awkward part is that `strip()` is needed twice: once to test and "
                    "once to transform. Calling it twice works and is a little wasteful."
                ),
                HintSpec(
                    "To call it once, use the walrus operator in the filter: "
                    "`[s.title() for name in raw if (s := name.strip())]` — an empty string "
                    "is falsy, so that filters blanks too."
                ),
            ),
            solution_files={
                "main.py": '''\
def clean_names(raw: list[str]) -> list[str]:
    """Strip, drop blanks, and title-case."""
    return [stripped.title() for name in raw if (stripped := name.strip())]
'''
            },
            solution_explanation="The walrus binds the stripped value inside the filter, so "
            "`strip()` runs once per name and the transform can reuse the result. The filter "
            "relies on an empty string being falsy, which is idiomatic Python — writing "
            '`!= ""` would be equally correct and slightly louder. Calling `name.strip()` '
            "twice also passes; it is simply work done twice for no reason.",
        ),
        ExerciseSpec(
            slug="comp-flatten-filter",
            title="Flatten and filter a nested structure",
            prompt="Write `positive_cells(grid)` taking a list of lists of numbers and "
            "returning a flat list of only the positive values, in row-major order "
            "(left to right, top to bottom).\n\n"
            "`[[1, -2], [0, 3]]` becomes `[1, 3]`. Rows may be empty.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.45,
            estimated_minutes=14,
            xp_reward=40,
            starter_files={
                "main.py": '''\
def positive_cells(grid: list[list[float]]) -> list[float]:
    """Flatten the grid, keeping only positive values."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_flatten.py": """\
from main import positive_cells


def test_flattens_and_filters():
    assert positive_cells([[1, -2], [0, 3]]) == [1, 3]


def test_row_major_order():
    assert positive_cells([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_zero_is_not_positive():
    assert positive_cells([[0]]) == []


def test_empty_grid():
    assert positive_cells([]) == []


def test_empty_rows_are_skipped():
    assert positive_cells([[], [5], []]) == [5]


def test_floats():
    assert positive_cells([[0.5, -0.5]]) == [0.5]


def test_all_negative():
    assert positive_cells([[-1, -2], [-3]]) == []
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("comprehensions", "lists"),
            hints=(
                HintSpec("A nested comprehension needs two `for` clauses in one expression."),
                HintSpec(
                    "They appear in the same order as nested loops: the outer loop over "
                    "rows comes first, then the inner loop over cells."
                ),
                HintSpec(
                    "The filter goes at the end and applies to the innermost variable. "
                    "Remember zero is not positive."
                ),
                HintSpec(
                    "`[cell for row in grid for cell in row if cell > 0]`. Empty rows need "
                    "no special case — the inner loop simply runs zero times."
                ),
            ),
            solution_files={
                "main.py": '''\
def positive_cells(grid: list[list[float]]) -> list[float]:
    """Flatten the grid, keeping only positive values."""
    return [cell for row in grid for cell in row if cell > 0]
'''
            },
            solution_explanation="Two `for` clauses flatten; the trailing `if` filters. Empty "
            "rows and an empty grid need no special handling, because iterating nothing "
            "produces nothing — one of the reasons this reads better than the loop version, "
            "which invites a needless `if not row: continue`.",
            misconception_rules=(
                {"pattern": "test_zero_is_not_positive", "misconception": "off-by-one"},
                {"pattern": "test_row_major_order", "misconception": "nested-comp-order"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 4 — Sorting
# ---------------------------------------------------------------------------

SORTING_AND_KEYS = LessonSpec(
    slug="sorting-and-keys",
    title="Sorting: Key Functions, Stability and Custom Order",
    summary="You almost never write a comparison. You write a function that says what to "
    "compare — and stability lets you build compound orders out of simple ones.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=30,
    xp_reward=40,
    concepts=("sorting", "tuples"),
    reference_keys=("sorted", "list.sort"),
    body="""\
## Two spellings, one of which returns nothing

```python
new = sorted(items)      # returns a new list; items untouched
items.sort()             # sorts in place; returns None
```

The single most common sorting bug in Python is this:

```python
items = items.sort()     # items is now None
```

Choose deliberately: `sorted()` when the original matters or the input is not a
list, `.sort()` when you own the list and want to avoid the copy.

## key= says what to compare

You do not write a comparator. You write a function that extracts the thing to
order by, and Python compares those:

```python
words = ["banana", "kiwi", "apple"]
sorted(words, key=len)                    # ['kiwi', 'apple', 'banana']
sorted(words, key=str.lower)              # case-insensitive
sorted(people, key=lambda p: p["age"])    # by a dict field
```

`key` is called **once per element**, not once per comparison, so an expensive
key function is fine. That is why this pattern beats writing comparisons: it is
both clearer and faster.

Note the shape: `key=len`, not `key=len()`. You pass the function itself.

## Tuples give you compound keys for free

Tuples compare element by element, so returning a tuple from `key` sorts by
several fields at once:

```python
sorted(people, key=lambda p: (p["last"], p["first"]))
```

Last name, then first name as a tie-break. To reverse just one field, negate it
when it is a number:

```python
sorted(items, key=lambda i: (-i["score"], i["name"]))   # score desc, name asc
```

There is no way to negate a string, which brings us to the better technique.

## Stability is a guarantee you can build on

Python's sort is **stable**: elements that compare equal keep their original
relative order. That means a compound sort can be done as a sequence of simple
sorts, applied **least significant first**:

```python
records.sort(key=lambda r: r["name"])              # tie-break
records.sort(key=lambda r: r["score"], reverse=True)  # primary
```

After the second sort, equal scores are still in name order, because the first
sort put them there and the second did not disturb them. This is the clean way
to sort descending by one field and ascending by another — no negation tricks,
and it works for strings.

## reverse= versus reversed()

```python
sorted(xs, reverse=True)     # sorted descending
reversed(sorted(xs))         # sorted ascending, then flipped
```

These differ when keys tie. `reverse=True` preserves the original order of equal
elements; reversing afterwards flips them. Prefer `reverse=True`.

## What cannot be sorted

```python
sorted([1, "two"])       # TypeError: '<' not supported between 'str' and 'int'
sorted([None, 1])        # TypeError
```

Sorting needs a total order. Mixed types usually mean the data needed cleaning
first, and a `key` that papers over it — `key=str` — produces an order nobody
asked for. Fix the data.

For objects, `key` is almost always better than defining `__lt__`: it keeps the
ordering decision at the call site, where the reader can see which of several
possible orders was intended.
""",
    sections={
        "what_is_it": "sorted() returns a new sorted list from any iterable; list.sort() "
        "reorders a list in place. Both take a key function that maps each element to the "
        "value actually compared, and a reverse flag.",
        "why_it_exists": "Ordering is needed constantly, and the thing to order by is usually "
        "not the element itself but something derived from it. Passing a key function keeps "
        "the ordering rule at the call site and lets the sort compare cheap extracted values "
        "rather than invoking user code for every comparison.",
        "how_it_works": "CPython uses Timsort, an adaptive merge sort that exploits runs "
        "already in order. It is stable, so equal keys retain input order, and O(n log n) in "
        "the worst case, approaching O(n) on nearly sorted data. The key function is applied "
        "once per element up front, and the resulting keys are what get compared.",
        "when_to_use": "Whenever output order matters to a human or to a downstream contract. "
        "Use a tuple key for multi-field order, and successive stable sorts when different "
        "fields need different directions.",
        "when_not_to_use": "When you only need the extreme values — min, max, or "
        "heapq.nlargest are O(n) where a full sort is O(n log n). When the data is already "
        "maintained in order. And when you need order *and* fast membership, where a sorted "
        "list plus bisect, or a different structure entirely, may fit better.",
        "common_mistakes": "Assigning the result of .sort() and getting None. Writing key=len() "
        "instead of key=len. Negating a string to reverse it. Assuming sorted() mutates, or "
        "that .sort() returns a list. Sorting mixed types and papering over the TypeError with "
        "key=str.",
        "real_world": "Leaderboards (score descending, name ascending); log lines by "
        "timestamp; a table the user clicked a column header on; ordering API results "
        "deterministically so that pagination is stable and tests are not flaky.",
        "alternatives": "min and max for single extremes; heapq.nlargest / nsmallest for a "
        "top-k slice; bisect.insort to keep a list sorted as it grows; ORDER BY in the "
        "database when the data comes from one — almost always faster than sorting in Python.",
        "performance": "O(n log n) comparisons, and O(n) key calls. Timsort is genuinely fast "
        "on partially ordered real-world data. A tuple key costs a small amount of tuple "
        "construction per element; two successive stable sorts cost roughly twice one sort, "
        "which is usually a fair price for the clarity.",
        "security": "Sorting untrusted data is safe, but sorting by a user-supplied field name "
        "is not if the name is used to reach into objects — validate it against an explicit "
        "allowlist of sortable fields rather than passing it to getattr. Unbounded sorts on "
        "attacker-controlled input are a memory and CPU denial-of-service vector.",
    },
    starter_code="""\
people = [
    {"name": "Ada", "score": 91},
    {"name": "Grace", "score": 91},
    {"name": "Alan", "score": 78},
]

# Least significant first, relying on stability.
people.sort(key=lambda p: p["name"])
people.sort(key=lambda p: p["score"], reverse=True)

for person in people:
    print(person["score"], person["name"])
""",
    examples=(
        Example(
            title="sort() returns None",
            code="items = [3, 1, 2]\nprint(items.sort())\nprint(items)",
            output="None\n[1, 2, 3]",
            explanation="The list was sorted; the call evaluated to None. `items = "
            "items.sort()` is how that becomes a bug in a different function.",
        ),
        Example(
            title="A tuple key sorts by several fields",
            code='rows = [("b", 2), ("a", 2), ("c", 1)]\nprint(sorted(rows, key=lambda r: (r[1], r[0])))',
            output="[('c', 1), ('a', 2), ('b', 2)]",
            explanation="Second field first, then the first field as tie-break. Tuples "
            "compare left to right, which is exactly the semantics wanted.",
        ),
        Example(
            title="Stability makes two simple sorts equal one compound sort",
            code='rows = [("Ada", 91), ("Grace", 91), ("Alan", 78)]\n'
            "by_name = sorted(rows, key=lambda r: r[0])\n"
            "result = sorted(by_name, key=lambda r: r[1], reverse=True)\nprint(result)",
            output="[('Ada', 91), ('Grace', 91), ('Alan', 78)]",
            explanation="Ada precedes Grace among the tied 91s because the first sort put "
            "them in that order and the stable second sort left it alone. No negation, and "
            "it works on strings.",
        ),
        Example(
            title="key is called once per element",
            code="calls = []\n\ndef noisy(x):\n    calls.append(x)\n    return x\n\n"
            "sorted([3, 1, 2], key=noisy)\nprint(len(calls))",
            output="3",
            explanation="Three elements, three key calls — not one per comparison. An "
            "expensive key function is therefore not the problem people expect it to be.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="sort-leaderboard",
            title="Rank a leaderboard",
            prompt='Write `leaderboard(players)` taking a list of dicts with `"name"` and '
            '`"score"` keys, and returning a new list sorted by **score descending**, with '
            "ties broken by **name ascending**.\n\n"
            "Do not modify the input list.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.4,
            estimated_minutes=14,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def leaderboard(players: list[dict]) -> list[dict]:
    """Score descending, then name ascending."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_leaderboard.py": """\
from main import leaderboard


def _names(result):
    return [p["name"] for p in result]


def test_sorts_by_score_descending():
    players = [{"name": "a", "score": 1}, {"name": "b", "score": 5}]
    assert _names(leaderboard(players)) == ["b", "a"]


def test_ties_broken_by_name_ascending():
    players = [
        {"name": "Grace", "score": 91},
        {"name": "Ada", "score": 91},
        {"name": "Alan", "score": 78},
    ]
    assert _names(leaderboard(players)) == ["Ada", "Grace", "Alan"]


def test_does_not_mutate_the_input():
    players = [{"name": "a", "score": 1}, {"name": "b", "score": 5}]
    leaderboard(players)
    assert _names(players) == ["a", "b"], "return a new list; do not sort in place"


def test_returns_a_list():
    assert isinstance(leaderboard([]), list)


def test_empty():
    assert leaderboard([]) == []


def test_single_player():
    assert _names(leaderboard([{"name": "solo", "score": 3}])) == ["solo"]
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("sorting",),
            hints=(
                HintSpec(
                    "`sorted()` returns a new list, which is what 'do not modify the input' "
                    "requires. `.sort()` would fail that test."
                ),
                HintSpec(
                    "The two fields sort in opposite directions, so a single `reverse=True` "
                    "cannot do both — it would reverse the names too."
                ),
                HintSpec(
                    "Either negate the numeric field in a tuple key — `(-score, name)` — or "
                    "do two stable sorts, least significant first."
                ),
                HintSpec(
                    'One line: `return sorted(players, key=lambda p: (-p["score"], '
                    'p["name"]))`. Negating works here because score is a number.'
                ),
            ),
            solution_files={
                "main.py": '''\
def leaderboard(players: list[dict]) -> list[dict]:
    """Score descending, then name ascending."""
    return sorted(players, key=lambda player: (-player["score"], player["name"]))
'''
            },
            solution_explanation="The tuple key sorts by two fields in one pass, and negating "
            "the score flips just that field. The equally valid alternative is two stable "
            "sorts — `sorted` by name, then by score with reverse=True — which is what you "
            "must use when the descending field is a string and cannot be negated.",
            misconception_rules=(
                {"pattern": "test_does_not_mutate_the_input", "misconception": "sort-returns-none"},
                {
                    "pattern": "test_ties_broken_by_name_ascending",
                    "misconception": "stability-ignored",
                },
            ),
        ),
        ExerciseSpec(
            slug="sort-none-debug",
            title="Debug: the function returns None",
            prompt="`top_three(scores)` should return the three highest scores, highest "
            "first. Every test fails with `TypeError: 'NoneType' object is not subscriptable`.\n\n"
            "Find and fix the cause. There is exactly one bug.",
            kind=ExerciseKind.DEBUG,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.3,
            estimated_minutes=12,
            xp_reward=30,
            starter_files={
                "main.py": '''\
def top_three(scores: list[int]) -> list[int]:
    """The three highest scores, highest first."""
    ordered = list(scores).sort(reverse=True)
    return ordered[:3]
'''
            },
            hidden_files={
                "test_top_three.py": """\
from main import top_three


def test_returns_highest_first():
    assert top_three([5, 1, 9, 3]) == [9, 5, 3]


def test_fewer_than_three():
    assert top_three([2, 7]) == [7, 2]


def test_empty():
    assert top_three([]) == []


def test_exactly_three():
    assert top_three([1, 2, 3]) == [3, 2, 1]


def test_does_not_mutate_the_input():
    original = [5, 1, 9]
    top_three(original)
    assert original == [5, 1, 9], "do not reorder the caller's list"


def test_duplicates_are_kept():
    assert top_three([4, 4, 4, 1]) == [4, 4, 4]
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("sorting",),
            hints=(
                HintSpec(
                    "The error says `ordered` is None. Something on the line above returned "
                    "None rather than a list."
                ),
                HintSpec("`list.sort()` sorts in place. Ask what it *returns* — not what it does."),
                HintSpec(
                    "You need the function that returns a new sorted list instead of "
                    "reordering one in place."
                ),
                HintSpec(
                    "`ordered = sorted(scores, reverse=True)`. That also drops the now "
                    "unnecessary `list(...)` copy, since sorted always builds a new list."
                ),
            ),
            solution_files={
                "main.py": '''\
def top_three(scores: list[int]) -> list[int]:
    """The three highest scores, highest first."""
    ordered = sorted(scores, reverse=True)
    return ordered[:3]
'''
            },
            solution_explanation="`sorted()` returns the new list that `.sort()` does not. The "
            "explicit `list(scores)` copy is redundant once you use sorted, and slicing past "
            "the end is not an error in Python, so the fewer-than-three case needs no guard.",
            misconception_rules=(
                {"pattern": "TypeError", "misconception": "sort-returns-none"},
                {"pattern": "test_does_not_mutate_the_input", "misconception": "sort-returns-none"},
            ),
        ),
        ExerciseSpec(
            slug="sort-group-order",
            title="Sort by a computed key",
            prompt="Write `by_extension(paths)` which sorts filenames by their extension "
            "(the text after the last `.`, compared case-insensitively), and within the same "
            "extension by the **full filename**, case-insensitively.\n\n"
            "A name with no `.` has an empty extension and sorts first. Return a new list.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.5,
            estimated_minutes=16,
            xp_reward=40,
            starter_files={
                "main.py": '''\
def by_extension(paths: list[str]) -> list[str]:
    """Sort by extension, then by full name — both case-insensitively."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_extension.py": """\
from main import by_extension


def test_groups_by_extension():
    assert by_extension(["b.py", "a.md", "c.py"]) == ["a.md", "b.py", "c.py"]


def test_no_extension_sorts_first():
    assert by_extension(["a.py", "README"]) == ["README", "a.py"]


def test_extension_case_is_ignored():
    assert by_extension(["b.PY", "a.py"]) == ["a.py", "b.PY"]


def test_name_case_is_ignored():
    assert by_extension(["B.py", "a.py"]) == ["a.py", "B.py"]


def test_empty():
    assert by_extension([]) == []


def test_does_not_mutate_the_input():
    original = ["b.py", "a.py"]
    by_extension(original)
    assert original == ["b.py", "a.py"]


def test_dotfile_has_no_extension():
    # ".gitignore" splits to ("", "gitignore") with rsplit, so treat a leading
    # dot as part of the name: there is no extension before the first character.
    assert by_extension([".gitignore", "a.py"]) == [".gitignore", "a.py"]
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("sorting", "strings"),
            hints=(
                HintSpec("The key needs two parts, so return a tuple: (extension, whole name)."),
                HintSpec(
                    '`name.rpartition(".")` splits at the *last* dot and always returns '
                    "three parts, so it does not raise when there is no dot."
                ),
                HintSpec(
                    "Case-insensitive comparison means lowercasing inside the key, not "
                    "lowercasing the values you return."
                ),
                HintSpec(
                    'With rpartition, `head, sep, tail = name.rpartition(".")`. If `head` '
                    "is empty there was no dot before any character, so the extension should "
                    "be treated as empty — that handles both `README` and `.gitignore`."
                ),
            ),
            solution_files={
                "main.py": '''\
def by_extension(paths: list[str]) -> list[str]:
    """Sort by extension, then by full name — both case-insensitively."""

    def key(name: str) -> tuple[str, str]:
        head, _, tail = name.rpartition(".")
        extension = tail.lower() if head else ""
        return (extension, name.lower())

    return sorted(paths, key=key)
'''
            },
            solution_explanation="A named inner function rather than a lambda, because the key "
            "needs two statements — which is the honest signal that a lambda has stopped "
            "being the right tool. `rpartition` never raises, and its empty `head` is exactly "
            "the 'no extension' case, covering both `README` and `.gitignore` without a "
            "special branch. Lowercasing happens in the key, so the returned strings keep "
            "their original case.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 5 — Complexity
# ---------------------------------------------------------------------------

COMPLEXITY_AND_CHOICE = LessonSpec(
    slug="complexity-and-structure-choice",
    title="Complexity: Choosing a Structure You Can Defend",
    summary="Big-O is not about speed. It is about what happens when the input gets ten "
    "times bigger — and it is the vocabulary for justifying a data structure in review.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=32,
    xp_reward=45,
    concepts=("complexity", "performance"),
    reference_keys=("dict", "set", "list"),
    body="""\
## What the notation actually claims

O(n) does not mean "slow" and O(1) does not mean "fast". They describe how cost
**grows** as the input grows:

| | ten times the input means |
| --- | --- |
| O(1) | the same cost |
| O(log n) | a little more — one extra step per doubling |
| O(n) | ten times the cost |
| O(n log n) | a bit over ten times |
| O(n²) | a **hundred** times the cost |

So an O(n) scan of 10 items beats an O(1) dict lookup that first has to build the
dict. Complexity tells you who wins *as n grows*, not who wins today. Both facts
matter, and only one of them is in the notation.

## What the standard containers cost

Worth knowing by heart, because most design decisions come down to this table:

```
                    list        dict / set      deque
index / key lookup  O(1)        O(1)            O(1) at the ends
membership (in)     O(n)        O(1)            O(n)
append / add        O(1)*       O(1)            O(1) both ends
insert at front     O(n)        —               O(1)
pop from front      O(n)        —               O(1)
delete by value     O(n)        O(1) by key     O(n)
ordered iteration   O(n)        O(n) insertion  O(n)
```

`*` amortised: an append is occasionally O(n) when the list grows its buffer, but
averages O(1) over many appends.

Two rows explain most accidental slowness: **membership on a list is O(n)**, and
**inserting or popping at the front of a list is O(n)**.

## The quadratic trap

This is the mistake to be able to spot instantly:

```python
# O(n * m): the `in` scans `banned` for every user
flagged = [u for u in users if u in banned]        # banned is a list
```

Nothing looks wrong. There is no nested loop on the page — the inner loop is
hidden inside `in`. The fix is one line:

```python
banned_set = set(banned)                            # O(m), once
flagged = [u for u in users if u in banned_set]     # O(n)
```

The same shape hides in `list.remove()` in a loop, `if x not in result` while
deduplicating, and `del items[0]` to consume a queue.

## Measure before you optimise anything

Complexity tells you which approach survives growth. It does not tell you where
your program actually spends its time — and intuition about that is famously
wrong.

```python
import time
start = time.perf_counter()
...
print(f"{time.perf_counter() - start:.3f}s")
```

For anything real, use `cProfile` to find the hot function and `timeit` to
compare two versions of it. The order is: make it correct, measure, *then* change
the thing the measurement pointed at. Choosing the right container up front is
free; rewriting a working function on a hunch is not.

## When the constant factor wins

- **Small n.** Below a few dozen items, a list scan beats building a set. If the
  collection is a fixed handful, stop thinking about it.
- **Built in C.** A O(n) scan inside `list.index` can beat a O(1) lookup written
  in a Python loop, because the constant factor differs by an order of magnitude.
- **Build cost.** A set is worth it when you test membership more than once or
  twice. For a single lookup, converting costs more than scanning.

## Space is a complexity too

`set(banned)` buys O(1) lookups with O(m) memory. Usually correct, sometimes
not: a set of ten million strings is real memory. A generator expression is O(1)
space where a list comprehension is O(n) — which is why
`sum(x * x for x in huge)` works and the bracketed version may not.
""",
    sections={
        "what_is_it": "Complexity analysis describes how an operation's time or memory cost "
        "grows as its input grows, expressed in big-O notation and stated for the dominant "
        "term only.",
        "why_it_exists": "Measured timings are specific to one machine, one dataset and one "
        "day. A growth rate is portable: it predicts what happens at ten or a thousand times "
        "the size, which is exactly the question that cannot be answered by testing on today's "
        "data. It is also the shared vocabulary for defending a design in review.",
        "how_it_works": "Count the operations that dominate as n grows and discard constants "
        "and lower-order terms, because they stop mattering. A nested loop over the same input "
        "is O(n^2); halving the search space each step is O(log n); a hash lookup is O(1) "
        "because it does not depend on how many items are stored.",
        "when_to_use": "When choosing a container, when reviewing a loop that contains a "
        "membership test or a search, and whenever the data is expected to grow. It is "
        "cheapest to get right while writing the code.",
        "when_not_to_use": "As a substitute for measurement on real data, or as a reason to "
        "complicate code that handles a fixed, small collection. An O(n^2) loop over five "
        "configuration entries is not a defect, and rewriting it is not an improvement.",
        "common_mistakes": "Treating big-O as a speed rating. Forgetting that `in` on a list "
        "is a hidden loop. Using a list as a queue with pop(0). Deduplicating with `if x not "
        "in result` on a list, which is quadratic. Optimising a function that was never the "
        "bottleneck because it looked slow.",
        "real_world": "The commonest real performance bug in Python services is a membership "
        "test against a list inside a request loop — imperceptible with test fixtures, "
        "crippling at production volume. The second commonest is a query in a loop, which is "
        "the same shape with a network round trip as the inner operation.",
        "alternatives": "cProfile and timeit to find and compare real costs; a database index "
        "when the data lives in a database, where the right index changes complexity in the "
        "engine rather than in Python; specialised structures such as heapq, bisect and "
        "collections.deque when the access pattern is the constraint.",
        "performance": "The whole lesson. The practical summary: sets and dicts for "
        "membership and keyed lookup, deque for queues, heapq for top-k, bisect for ordered "
        "search, and lists for everything ordered you iterate over. Then measure.",
        "security": "Complexity is an attack surface. If an attacker chooses the input size or "
        "content, a quadratic path becomes a denial of service, and unbounded growth becomes "
        "memory exhaustion. Validate and bound untrusted input before it reaches a structure "
        "whose cost depends on it — this is the class of bug behind hash-collision attacks.",
    },
    starter_code="""\
import time

names = [f"user{i}" for i in range(20_000)]
lookup_list = names
lookup_set = set(names)

for label, collection in (("list", lookup_list), ("set", lookup_set)):
    start = time.perf_counter()
    hits = sum(1 for n in names[:2_000] if n in collection)
    print(f"{label:5} {hits} hits in {time.perf_counter() - start:.4f}s")
""",
    examples=(
        Example(
            title="The same code, two complexities",
            code='users = [f"u{i}" for i in range(5)]\nbanned_list = [f"u{i}" for i in range(3)]\n'
            "banned_set = set(banned_list)\n"
            "print([u for u in users if u in banned_list])\n"
            "print([u for u in users if u in banned_set])",
            output="['u0', 'u1', 'u2']\n['u0', 'u1', 'u2']",
            explanation="Identical output. At five items the difference is unmeasurable; at "
            "fifty thousand the first is a hundred million comparisons and the second is not.",
        ),
        Example(
            title="A list is a bad queue",
            code="from collections import deque\n\nq = deque([1, 2, 3])\nprint(q.popleft())\n"
            "lst = [1, 2, 3]\nprint(lst.pop(0))",
            output="1\n1",
            explanation="Same answer. `deque.popleft()` is O(1); `list.pop(0)` shifts every "
            "remaining element, so draining a list this way is O(n^2).",
        ),
        Example(
            title="Quadratic deduplication, hiding in plain sight",
            code="items = [1, 2, 1, 3, 2]\nresult = []\nfor x in items:\n"
            "    if x not in result:\n        result.append(x)\nprint(result)",
            output="[1, 2, 3]",
            explanation="Correct, and O(n^2) — `x not in result` scans the growing list every "
            "time. `list(dict.fromkeys(items))` is O(n) and shorter.",
        ),
        Example(
            title="Space complexity is real",
            code="print(sum(x * x for x in range(1_000_000)))",
            output="333332833333500000",
            explanation="The generator holds one value at a time. The list-comprehension "
            "version would allocate a million integers to produce the same number.",
        ),
    ),
    visualizations=(
        {
            "kind": "growth",
            "title": "Cost at n, 10n and 100n",
            "series": [
                {"label": "O(1)", "values": [1, 1, 1]},
                {"label": "O(log n)", "values": [1, 2, 3]},
                {"label": "O(n)", "values": [1, 10, 100]},
                {"label": "O(n log n)", "values": [1, 20, 300]},
                {"label": "O(n^2)", "values": [1, 100, 10000]},
            ],
        },
    ),
    exercises=(
        ExerciseSpec(
            slug="complexity-fix-quadratic",
            title="Make the filter linear",
            prompt="`flag_users(users, banned)` is correct but quadratic: it scans `banned` "
            "once for every user.\n\n"
            "Rewrite it so the total work is linear in `len(users) + len(banned)`, keeping the "
            "output identical — the flagged users in their original order.\n\n"
            "The hidden tests include one that times a large input, so an O(n*m) solution "
            "will fail rather than merely be criticised.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.5,
            estimated_minutes=16,
            xp_reward=45,
            starter_files={
                "main.py": '''\
def flag_users(users: list[str], banned: list[str]) -> list[str]:
    """Return the users who appear in banned, in their original order."""
    flagged = []
    for user in users:
        if user in banned:      # O(len(banned)) every time round the loop
            flagged.append(user)
    return flagged
'''
            },
            hidden_files={
                "test_flag.py": """\
import time

from main import flag_users


def test_finds_banned_users():
    assert flag_users(["a", "b", "c"], ["c", "a"]) == ["a", "c"]


def test_preserves_user_order():
    assert flag_users(["z", "y", "x"], ["x", "y", "z"]) == ["z", "y", "x"]


def test_none_banned():
    assert flag_users(["a"], []) == []


def test_empty_users():
    assert flag_users([], ["a"]) == []


def test_duplicate_users_are_all_flagged():
    assert flag_users(["a", "a"], ["a"]) == ["a", "a"]


def test_is_linear_not_quadratic():
    # 60k users against 30k banned names. Measured: the set-based solution takes
    # ~2ms, the list-scanning original ~5.2s, because `in` on a list is a scan.
    # The 1s threshold sits between them with ~500x headroom for a correct
    # solution, so it stays decisive on a much faster machine and does not turn
    # into a flaky test.
    users = [f"user{i}" for i in range(60_000)]
    banned = [f"user{i}" for i in range(0, 60_000, 2)]
    start = time.perf_counter()
    result = flag_users(users, banned)
    elapsed = time.perf_counter() - start
    assert len(result) == 30_000
    assert elapsed < 1.0, (
        f"took {elapsed:.1f}s — still scanning a list for every user. "
        "Convert banned to a set once, before the loop."
    )
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("complexity", "sets"),
            hints=(
                HintSpec(
                    "The loop over users is unavoidable — you must look at each one. The "
                    "cost is in what happens *inside* it."
                ),
                HintSpec(
                    "`user in banned` searches a list, which is O(n). Which built-in "
                    "container answers the same question in O(1)?"
                ),
                HintSpec(
                    "Build the set once, before the loop. Building it inside the loop would "
                    "be just as quadratic as the original."
                ),
                HintSpec(
                    "`banned_set = set(banned)` above the loop, then test `user in "
                    "banned_set`. Order is preserved because you still iterate users in order."
                ),
            ),
            solution_files={
                "main.py": '''\
def flag_users(users: list[str], banned: list[str]) -> list[str]:
    """Return the users who appear in banned, in their original order."""
    banned_set = set(banned)
    return [user for user in users if user in banned_set]
'''
            },
            solution_explanation="Building the set is O(len(banned)) once; each membership "
            "test is then O(1), so the total is linear. Output order is unchanged because the "
            "iteration is still over `users` — the set is only consulted, never iterated, "
            "which is what makes this safe despite sets being unordered.",
            misconception_rules=(
                {"pattern": "test_is_linear_not_quadratic", "misconception": "in-is-cheap"},
            ),
        ),
        ExerciseSpec(
            slug="complexity-word-counts",
            title="Count with the right structure",
            prompt="Write `top_words(text, n)` returning the `n` most frequent words in "
            "`text` as a list of `(word, count)` tuples, most frequent first, ties broken "
            "alphabetically.\n\n"
            "Words are whitespace-separated and compared lower-case. The whole function must "
            "be O(w log w) or better for `w` words — counting by scanning a list of seen "
            "words will time out.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.55,
            estimated_minutes=18,
            xp_reward=45,
            starter_files={
                "main.py": '''\
def top_words(text: str, n: int) -> list[tuple[str, int]]:
    """The n most frequent words, most frequent first, ties alphabetical."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_words.py": """\
import time

from main import top_words


def test_counts_and_ranks():
    assert top_words("a b a c a b", 2) == [("a", 3), ("b", 2)]


def test_ties_are_alphabetical():
    assert top_words("b a", 2) == [("a", 1), ("b", 1)]


def test_case_is_ignored():
    assert top_words("The the THE", 1) == [("the", 3)]


def test_returns_tuples():
    first = top_words("a", 1)[0]
    assert isinstance(first, tuple) and len(first) == 2


def test_n_larger_than_vocabulary():
    assert top_words("a b", 10) == [("a", 1), ("b", 1)]


def test_empty_text():
    assert top_words("", 3) == []


def test_zero_n():
    assert top_words("a b", 0) == []


def test_scales():
    # 200k words over a 5k vocabulary. Counting into a dict is instant;
    # scanning a list of seen words for each is ~10^9 comparisons.
    words = " ".join(f"w{i % 5_000}" for i in range(200_000))
    start = time.perf_counter()
    result = top_words(words, 5)
    elapsed = time.perf_counter() - start
    assert len(result) == 5
    assert elapsed < 3.0, (
        f"took {elapsed:.1f}s — count with a dict or Counter, "
        "not by searching a list of words already seen."
    )
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("complexity", "dictionaries", "sorting"),
            hints=(
                HintSpec(
                    "Counting occurrences is a keyed-lookup problem, so it wants a dict — or "
                    "`collections.Counter`, which is a dict specialised for exactly this."
                ),
                HintSpec(
                    "`text.lower().split()` gives the words. `split()` with no argument "
                    "splits on any whitespace and discards empties, which handles the empty "
                    "string for free."
                ),
                HintSpec(
                    "Two sort directions again: count descending, word ascending. A tuple "
                    "key with the count negated does it — `(-count, word)`."
                ),
                HintSpec(
                    "`counts = Counter(text.lower().split())`, then "
                    "`sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]`. "
                    "Counter.most_common does not break ties alphabetically, so sort yourself."
                ),
            ),
            solution_files={
                "main.py": '''\
from collections import Counter


def top_words(text: str, n: int) -> list[tuple[str, int]]:
    """The n most frequent words, most frequent first, ties alphabetical."""
    counts = Counter(text.lower().split())
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]
'''
            },
            solution_explanation="Counting is O(w) through a hash table; the sort is "
            "O(v log v) in the vocabulary size, which is what dominates. `most_common(n)` "
            "would be tempting and is subtly wrong here — it does not specify a tie-break, so "
            "equal counts come out in insertion order rather than alphabetically. Slicing "
            "after the sort handles both `n` larger than the vocabulary and `n == 0` without "
            "a guard.",
            misconception_rules=(
                {"pattern": "test_scales", "misconception": "in-is-cheap"},
                {"pattern": "test_ties_are_alphabetical", "misconception": "stability-ignored"},
            ),
        ),
        ExerciseSpec(
            slug="complexity-pick-structure",
            title="Which structure, and why?",
            prompt="A service holds 2 million session IDs. The only operations are: add an "
            "ID, remove an ID, and check whether an ID is present — millions of times a "
            "minute. Order is never needed.\n\n"
            "Which is the defensible choice?",
            kind=ExerciseKind.QUIZ,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.35,
            estimated_minutes=6,
            xp_reward=20,
            grader=GraderKind.MULTIPLE_CHOICE,
            grader_config={
                "options": [
                    "A list, because appending is O(1) and it uses the least memory.",
                    "A sorted list with bisect, because binary search is O(log n).",
                    "A set, because add, remove and membership are all O(1) and order is "
                    "not required.",
                    "A dict mapping each ID to True, because dict lookup is faster than set "
                    "lookup.",
                ],
                "correct_index": 2,
            },
            concepts=("complexity", "sets"),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 6 — Queues and heaps
# ---------------------------------------------------------------------------

STACKS_QUEUES_HEAPS = LessonSpec(
    slug="stacks-queues-heaps",
    title="Stacks, Queues and Heaps From the Standard Library",
    summary="Three access patterns — last-in-first-out, first-in-first-out, and "
    "smallest-first — each with a container that makes it O(1) instead of O(n).",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=32,
    xp_reward=45,
    concepts=("stacks-queues", "heaps", "searching"),
    reference_keys=("list.append", "sorted"),
    body="""\
## A list is already a good stack

Last in, first out needs nothing special — both operations are at the end, where
a list is fast:

```python
stack = []
stack.append(1)
stack.append(2)
stack.pop()          # 2 — O(1)
```

Undo history, bracket matching, depth-first traversal, and the interpreter's own
call stack are all this shape.

## A list is a bad queue, and it is not obvious

First in, first out means taking from the *front*, and that is where a list is
slow:

```python
queue = [1, 2, 3]
queue.pop(0)         # 1 — but every remaining element shifts left. O(n).
```

Draining n items that way is O(n²). Use `collections.deque`, which is O(1) at
both ends:

```python
from collections import deque

queue = deque([1, 2, 3])
queue.append(4)      # push right
queue.popleft()      # 1 — pop left, O(1)
```

`deque` also takes `maxlen`, which makes a fixed-size sliding window trivial —
pushing past the limit discards from the other end:

```python
last_three = deque(maxlen=3)
for item in stream:
    last_three.append(item)      # only ever holds the newest three
```

The trade: `deque` gives up cheap indexing in the middle. `d[0]` is fine,
`d[n // 2]` is O(n). If you need random access, you wanted a list.

## A heap is for "smallest first", cheaply

Sorting to find the smallest item is O(n log n) and does far more work than
asked. A heap keeps only enough order to know the minimum:

```python
import heapq

h = [5, 1, 3]
heapq.heapify(h)        # O(n), in place
heapq.heappush(h, 2)    # O(log n)
heapq.heappop(h)        # 1 — the smallest. O(log n)
```

There is no heap *type* — `heapq` operates on a plain list, maintaining an
invariant inside it. So this is expected and not a bug:

```python
print(h)     # e.g. [2, 5, 3] — index 0 is the smallest; the rest is a shape, not an order
```

Only `h[0]` is meaningful. Printing a heap and expecting sorted output is the
classic misunderstanding.

### Priorities, and the max-heap problem

`heapq` is min-only. For a max-heap, negate:

```python
heapq.heappush(h, -score)
biggest = -heapq.heappop(h)
```

For "smallest priority first, carrying a payload", push tuples — they compare
left to right:

```python
heapq.heappush(tasks, (priority, counter, task))
```

The middle `counter` is a tie-breaker that keeps insertion order among equal
priorities *and* avoids comparing `task` at all — which matters when the payload
is a dict or an object that cannot be ordered.

### Top-k is the killer use

```python
heapq.nlargest(10, items, key=lambda i: i["score"])
```

O(n log k) rather than the O(n log n) of a full sort. When k is small and n is
large — the top ten of a million — this is the right tool. When k approaches n,
just sort.

## bisect, when the list is already sorted

If you maintain order, binary search finds a position in O(log n):

```python
import bisect

scores = [10, 20, 30]
bisect.bisect_left(scores, 20)      # 1 — where it is, or would go
bisect.insort(scores, 25)           # [10, 20, 25, 30]
```

`bisect` **assumes** the input is sorted and does not check. On unsorted data it
returns a confident wrong answer rather than raising — worse than a crash. And
note `insort` is O(n) despite the O(log n) search, because inserting into the
middle of a list shifts everything after it. It is right for read-heavy data,
wrong for a write-heavy queue.

## Choosing

| Need | Use |
| --- | --- |
| last in, first out | `list` with append/pop |
| first in, first out | `collections.deque` |
| fixed-size recent window | `deque(maxlen=k)` |
| repeatedly take the smallest | `heapq` |
| top k of many | `heapq.nlargest` |
| position in sorted data | `bisect` |
| everything at once, ordered | `sorted()` |
""",
    sections={
        "what_is_it": "Three access patterns and their standard-library containers: a list as "
        "a stack, collections.deque as a double-ended queue, and heapq maintaining a min-heap "
        "invariant inside a plain list — plus bisect for binary search over sorted sequences.",
        "why_it_exists": "Each pattern has an operation that a plain list makes O(n): popping "
        "from the front, or finding the smallest. Specialised structures trade capabilities "
        "they do not need — random access for a deque, full ordering for a heap — to make the "
        "one operation you do need constant or logarithmic.",
        "how_it_works": "A deque is a doubly linked list of blocks, so both ends are cheap and "
        "the middle is not. A heap is an array-backed binary tree where every parent is no "
        "greater than its children, which is weak enough to maintain in O(log n) and strong "
        "enough to make the minimum index 0. bisect halves a sorted range each step.",
        "when_to_use": "deque for queues, BFS frontiers and sliding windows; heapq for "
        "priority scheduling, merging sorted streams and top-k; bisect for lookups and "
        "insertions in data you keep sorted; a list for stacks.",
        "when_not_to_use": "deque when you need indexing or slicing in the middle. heapq when "
        "you need the full order — sort instead — or when k approaches n. bisect on data you "
        "cannot guarantee is sorted, or that changes often, since each insort is O(n).",
        "common_mistakes": "Using list.pop(0) as a queue. Printing a heap and expecting sorted "
        "output. Forgetting heapq is min-only and building a max-heap without negating. "
        "Pushing tuples whose payload is compared on ties and raises TypeError. Running bisect "
        "on unsorted input and trusting the answer.",
        "real_world": "Task queues ordered by priority; breadth-first search over a graph or "
        "filesystem; the last N log lines held for a crash report; merging sorted files without "
        "loading them; leaderboards that only ever show the top ten; rate limiters holding a "
        "window of recent timestamps.",
        "alternatives": "queue.Queue when the queue must be thread-safe — deque is only safe "
        "for append and pop, not for compound operations; asyncio.Queue in async code; "
        "sortedcontainers (third party) for a structure that is genuinely sorted and cheap to "
        "insert into; a database with an index when the data outlives the process.",
        "performance": "deque append and pop at either end are O(1); indexing the middle is "
        "O(n). heapify is O(n), push and pop are O(log n), and reading the minimum is O(1). "
        "nlargest is O(n log k). bisect searches in O(log n) but insort is O(n) because of the "
        "shift, which is the detail people miss.",
        "security": "An unbounded queue fed by untrusted input is a memory-exhaustion vector; "
        "deque(maxlen=...) bounds it by construction, and a bounded queue.Queue rejects rather "
        "than growing. If an attacker controls priorities, they control scheduling order — do "
        "not let untrusted values decide what runs first.",
    },
    starter_code="""\
import heapq
from collections import deque

queue = deque(["first", "second"])
queue.append("third")
print("served:", queue.popleft(), "| waiting:", list(queue))

window = deque(maxlen=3)
for n in range(6):
    window.append(n)
print("last three:", list(window))

tasks = []
for priority, name in ((3, "email"), (1, "alert"), (2, "report")):
    heapq.heappush(tasks, (priority, name))
print("next:", heapq.heappop(tasks))
""",
    examples=(
        Example(
            title="deque is cheap at both ends",
            code="from collections import deque\n\nd = deque([2, 3])\nd.appendleft(1)\n"
            "d.append(4)\nprint(list(d), d.popleft(), d.pop())",
            output="[1, 2, 3, 4] 1 4",
            explanation="Four O(1) operations. The list equivalents, `insert(0, x)` and "
            "`pop(0)`, are both O(n).",
        ),
        Example(
            title="A heap is not a sorted list",
            code="import heapq\n\nh = [5, 1, 3, 2]\nheapq.heapify(h)\nprint(h)\nprint(h[0])",
            output="[1, 2, 3, 5]\n1",
            explanation="Here it happens to look sorted; with other inputs it will not, and "
            "that is still correct. Only `h[0]` is guaranteed to be the smallest.",
        ),
        Example(
            title="maxlen makes a sliding window free",
            code="from collections import deque\n\nw = deque(maxlen=3)\n"
            "for n in [1, 2, 3, 4, 5]:\n    w.append(n)\nprint(list(w))",
            output="[3, 4, 5]",
            explanation="Appending past maxlen discards from the opposite end. No length "
            "check, no slicing, no off-by-one.",
        ),
        Example(
            title="Top-k without a full sort",
            code="import heapq\n\nscores = [5, 82, 13, 99, 41]\nprint(heapq.nlargest(2, scores))",
            output="[99, 82]",
            explanation="O(n log k) with k=2. Sorting all five to look at two would be "
            "wasteful — and at a million items, wasteful becomes prohibitive.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="queue-service-order",
            title="Serve a queue in order",
            prompt="Write `serve(arrivals, capacity)` simulating a service desk.\n\n"
            "Process `arrivals` (a list of names) in order. The waiting area holds at most "
            "`capacity` people: someone arriving when it is full is turned away. After every "
            "two arrivals that join the queue, the person who has waited longest is served.\n\n"
            "Return `(served, turned_away)` — two lists, each in the order the events "
            "happened. Anyone still waiting at the end is neither served nor turned away.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.55,
            estimated_minutes=18,
            xp_reward=45,
            starter_files={
                "main.py": '''\
from collections import deque


def serve(arrivals: list[str], capacity: int) -> tuple[list[str], list[str]]:
    """Simulate the desk. Returns (served, turned_away)."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_serve.py": """\
from main import serve


def test_serves_longest_waiting_first():
    served, turned_away = serve(["a", "b"], 10)
    assert served == ["a"]
    assert turned_away == []


def test_serves_after_every_second_joiner():
    served, _ = serve(["a", "b", "c", "d"], 10)
    assert served == ["a", "b"]


def test_turns_away_when_full():
    served, turned_away = serve(["a", "b", "c"], 1)
    # a joins; b is refused (a still waiting, capacity 1); c is refused too.
    assert turned_away == ["b", "c"]
    assert served == []


def test_leftovers_are_not_served():
    served, turned_away = serve(["a"], 5)
    assert served == []
    assert turned_away == []


def test_empty_arrivals():
    assert serve([], 3) == ([], [])


def test_returns_two_lists():
    result = serve(["a", "b"], 2)
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(part, list) for part in result)


def test_capacity_frees_up_after_serving():
    # a, b join -> b is the second joiner so a is served, freeing space for c.
    served, turned_away = serve(["a", "b", "c"], 2)
    assert served == ["a"]
    assert turned_away == []
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("stacks-queues",),
            hints=(
                HintSpec(
                    "'The person who has waited longest' is first-in-first-out, so the "
                    "waiting area is a queue, not a stack."
                ),
                HintSpec(
                    "`deque.popleft()` takes the longest-waiting person in O(1). Use "
                    "`len(queue)` against `capacity` to decide whether someone can join."
                ),
                HintSpec(
                    "Count only the arrivals that actually *join*. Someone turned away must "
                    "not advance the counter, or the serving rhythm drifts."
                ),
                HintSpec(
                    "Keep a `joined` counter. On each arrival: if the queue is full, append "
                    "to turned_away and continue; otherwise append to the queue, increment "
                    "joined, and when `joined % 2 == 0` popleft into served."
                ),
            ),
            solution_files={
                "main.py": '''\
from collections import deque


def serve(arrivals: list[str], capacity: int) -> tuple[list[str], list[str]]:
    """Simulate the desk. Returns (served, turned_away)."""
    waiting: deque[str] = deque()
    served: list[str] = []
    turned_away: list[str] = []
    joined = 0

    for person in arrivals:
        if len(waiting) >= capacity:
            turned_away.append(person)
            continue
        waiting.append(person)
        joined += 1
        if joined % 2 == 0:
            served.append(waiting.popleft())

    return (served, turned_away)
'''
            },
            solution_explanation="A deque because both ends are used: arrivals push right, "
            "service pops left, each O(1). The counter increments only for people who join, "
            "which is what keeps 'every two arrivals' meaning what the specification says — "
            "counting every arrival would let a rejection advance the rhythm. Leftovers "
            "simply stay in `waiting` and are never reported, which the tests pin down.",
            misconception_rules=(
                {"pattern": "test_serves_longest_waiting_first", "misconception": "list-as-queue"},
                {
                    "pattern": "test_capacity_frees_up_after_serving",
                    "misconception": "off-by-one",
                },
            ),
        ),
        ExerciseSpec(
            slug="heap-top-scores",
            title="Top k without sorting everything",
            prompt="Write `top_k(records, k)` returning the `k` records with the highest "
            '`"score"`, highest first, as a list of the record dicts.\n\n'
            'Break ties by `"name"` ascending. Use `heapq` rather than sorting the whole '
            "input — with a million records and k=10 the difference is the point.\n\n"
            "`k` may exceed the number of records.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.ADVANCED,
            difficulty=0.6,
            estimated_minutes=18,
            xp_reward=50,
            starter_files={
                "main.py": '''\
import heapq


def top_k(records: list[dict], k: int) -> list[dict]:
    """The k highest-scoring records, highest first, ties by name ascending."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_top_k.py": """\
from main import top_k


def _names(result):
    return [r["name"] for r in result]


def test_returns_highest_first():
    records = [
        {"name": "a", "score": 10},
        {"name": "b", "score": 30},
        {"name": "c", "score": 20},
    ]
    assert _names(top_k(records, 2)) == ["b", "c"]


def test_ties_broken_by_name():
    records = [{"name": "zoe", "score": 5}, {"name": "amy", "score": 5}]
    assert _names(top_k(records, 2)) == ["amy", "zoe"]


def test_k_larger_than_input():
    records = [{"name": "a", "score": 1}]
    assert _names(top_k(records, 10)) == ["a"]


def test_k_zero():
    assert top_k([{"name": "a", "score": 1}], 0) == []


def test_empty_records():
    assert top_k([], 5) == []


def test_returns_the_record_dicts():
    record = {"name": "a", "score": 1}
    assert top_k([record], 1)[0] is record, "return the records themselves"


def test_does_not_mutate_the_input():
    records = [{"name": "a", "score": 1}, {"name": "b", "score": 2}]
    top_k(records, 1)
    assert _names(records) == ["a", "b"], "do not reorder the caller's list"


def test_records_with_unorderable_extras():
    # A payload containing a dict cannot be compared. If the heap ever tries to
    # order two records directly, this raises TypeError.
    records = [
        {"name": "a", "score": 1, "meta": {"x": 1}},
        {"name": "b", "score": 1, "meta": {"y": 2}},
    ]
    assert _names(top_k(records, 2)) == ["a", "b"]
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("heaps", "sorting"),
            hints=(
                HintSpec(
                    "`heapq.nlargest` takes a `key=` function, just like `sorted`, and is "
                    "O(n log k) instead of O(n log n)."
                ),
                HintSpec(
                    "Two directions again: score descending, name ascending. Since nlargest "
                    "takes the *largest* keys, the name part has to be inverted relative to "
                    "the score part."
                ),
                HintSpec(
                    "There is no way to negate a string. But `nsmallest` with `(-score, "
                    "name)` gives the same ranking with both fields in their natural "
                    "direction — smallest negated score is the highest score."
                ),
                HintSpec(
                    '`heapq.nsmallest(k, records, key=lambda r: (-r["score"], r["name"]))`. '
                    "The key means records are never compared with each other, which is why "
                    "the unorderable-payload test passes."
                ),
            ),
            solution_files={
                "main.py": '''\
import heapq


def top_k(records: list[dict], k: int) -> list[dict]:
    """The k highest-scoring records, highest first, ties by name ascending."""
    return heapq.nsmallest(k, records, key=lambda record: (-record["score"], record["name"]))
'''
            },
            solution_explanation="`nsmallest` with a negated score is the trick: it puts the "
            "highest scores first while leaving `name` ascending, which `nlargest` cannot do "
            "without a negatable string. Passing `key=` matters for more than ordering — the "
            "heap compares only the extracted tuples, so records holding unorderable values "
            "like a nested dict never get compared and cannot raise TypeError. Both nsmallest "
            "and nlargest handle k greater than the input and k of zero without a guard.",
            misconception_rules=(
                {"pattern": "test_records_with_unorderable_extras", "misconception": "heap-max"},
                {"pattern": "test_ties_broken_by_name", "misconception": "heap-is-sorted"},
            ),
        ),
        ExerciseSpec(
            slug="bisect-insert-position",
            title="Insert into sorted data",
            prompt="Write `add_score(scores, value)` which inserts `value` into the "
            "already-sorted ascending list `scores`, keeping it sorted, and returns the index "
            "the value was placed at.\n\n"
            "Mutate the list in place. Equal values must be inserted **after** any existing "
            "equal values. Do not re-sort the list — find the position by binary search.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.5,
            estimated_minutes=15,
            xp_reward=40,
            starter_files={
                "main.py": '''\
import bisect


def add_score(scores: list[int], value: int) -> int:
    """Insert value keeping scores sorted; return the index used."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_bisect.py": """\
from main import add_score


def test_inserts_in_the_middle():
    scores = [10, 20, 30]
    index = add_score(scores, 25)
    assert scores == [10, 20, 25, 30]
    assert index == 2


def test_inserts_at_the_start():
    scores = [10, 20]
    assert add_score(scores, 5) == 0
    assert scores == [5, 10, 20]


def test_inserts_at_the_end():
    scores = [10, 20]
    assert add_score(scores, 30) == 2
    assert scores == [10, 20, 30]


def test_equal_values_go_after():
    scores = [10, 20, 20, 30]
    index = add_score(scores, 20)
    assert index == 3, "an equal value belongs after the existing ones"
    assert scores == [10, 20, 20, 20, 30]


def test_empty_list():
    scores = []
    assert add_score(scores, 7) == 0
    assert scores == [7]


def test_mutates_in_place():
    scores = [1, 3]
    returned = add_score(scores, 2)
    assert scores == [1, 2, 3], "modify the list given, do not return a new one"
    assert isinstance(returned, int)
"""
            },
            grader=GraderKind.PYTEST,
            concepts=("searching", "stacks-queues"),
            hints=(
                HintSpec(
                    "The `bisect` module finds insertion points in sorted sequences by "
                    "binary search."
                ),
                HintSpec(
                    "`bisect_left` and `bisect_right` differ only in where they put a value "
                    "equal to existing ones. Read the requirement again and pick."
                ),
                HintSpec(
                    "You need both the index (to return) and the insertion (to mutate). "
                    "`list.insert(index, value)` does the second."
                ),
                HintSpec(
                    "`index = bisect.bisect_right(scores, value)` then "
                    "`scores.insert(index, value)`, and return index. "
                    "`bisect.insort_right` does both but does not give you the index back."
                ),
            ),
            solution_files={
                "main.py": '''\
import bisect


def add_score(scores: list[int], value: int) -> int:
    """Insert value keeping scores sorted; return the index used."""
    index = bisect.bisect_right(scores, value)
    scores.insert(index, value)
    return index
'''
            },
            solution_explanation="`bisect_right` returns the position *after* any equal "
            "values, which is exactly the stated requirement — `bisect_left` would return 1 "
            "instead of 3 in the duplicates test. `insort_right` would do both steps in one "
            "call, but it returns None, so the index has to be found separately anyway. The "
            "search is O(log n); the insert is still O(n) because the tail has to shift, "
            "which is the honest cost of keeping a list sorted.",
            misconception_rules=(
                {"pattern": "test_equal_values_go_after", "misconception": "off-by-one"},
                {"pattern": "test_mutates_in_place", "misconception": "sort-returns-none"},
            ),
        ),
    ),
)

ALGORITHMS_MODULE = ModuleSpec(
    slug="data-structures-and-algorithms",
    title="Data Structures and Algorithms: Choosing, and Justifying",
    summary="Tuples, sets, comprehensions, sorting, complexity and the queue and heap types "
    "in the standard library — the vocabulary for picking a container and defending the pick.",
    level=SkillLevel.INTERMEDIATE,
    lessons=(
        TUPLES_AND_UNPACKING,
        SETS_AND_MEMBERSHIP,
        COMPREHENSIONS_IN_DEPTH,
        SORTING_AND_KEYS,
        COMPLEXITY_AND_CHOICE,
        STACKS_QUEUES_HEAPS,
    ),
)
