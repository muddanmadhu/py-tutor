"""Additional Python Reference entries.

Split from :mod:`app.content.reference_entries` to keep either file readable.

These were chosen from evidence rather than taste: an audit found that 18 of the
19 lessons cited ``reference_keys`` with no matching entry, so the "look this up"
links were dead across nearly the whole curriculum. Every key those lessons cite
is defined here, plus the standard-library APIs the data-structures module teaches
(``deque``, ``heapq``, ``bisect``, ``Counter``) which a learner will reach for
immediately afterwards.

The format answers what someone needs at the moment they look something up:
signature, what it returns, a runnable example, the mistake people actually make,
and what to use instead. ``keywords`` carries search terms that are not in the
title — that is how "how do I count things" finds ``collections.Counter``.
"""

from __future__ import annotations

from app.content.schema import ReferenceSpec

BUILTIN_TYPES: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        key="int",
        title="int()",
        kind="class",
        module="builtins",
        signature="int(x=0, base=10) -> int",
        summary="Convert a number or string to an integer, truncating towards zero.",
        description="Parsing text to int is the boundary where bad input should be caught. "
        "`int` raises rather than guessing, which is what you want — a silent 0 from a "
        "malformed field is far worse than a ValueError at the point of entry.",
        parameters=(
            {
                "name": "x",
                "type": "str | float | int",
                "required": False,
                "default": "0",
                "description": "Value to convert.",
            },
            {
                "name": "base",
                "type": "int",
                "required": False,
                "default": "10",
                "description": "Radix, when x is a string. 0 means infer from a prefix.",
            },
        ),
        returns="An int.",
        raises=(
            {"error": "ValueError", "when": "The string is not a valid integer in that base."},
            {"error": "TypeError", "when": "x is None or another non-convertible type."},
        ),
        examples=(
            {"title": "From text", "code": "print(int('42') + 1)", "output": "43"},
            {
                "title": "Truncation, not rounding",
                "code": "print(int(2.9), int(-2.9))",
                "output": "2 -2",
            },
            {
                "title": "A decimal string is not an integer",
                "code": "print(int('12.5'))",
                "output": "ValueError: invalid literal for int() with base 10: '12.5'",
            },
            {"title": "Hex", "code": "print(int('ff', 16))", "output": "255"},
        ),
        real_world_usage="Converting CSV and form fields, parsing IDs from a URL path, "
        "reading numeric environment variables.",
        common_mistakes=(
            {
                "mistake": "int('12.5')",
                "fix": "int() parses integers only. Use float('12.5') first, then int() if "
                "you actually want truncation.",
            },
            {
                "mistake": "Expecting int(2.7) to round to 3",
                "fix": "It truncates towards zero. Use round(2.7) for rounding.",
            },
            {
                "mistake": "Wrapping every int() in a bare try/except",
                "fix": "Catch ValueError specifically, and only where you can do something "
                "useful about it.",
            },
        ),
        performance_notes="Python ints are arbitrary precision, so large values cost more "
        "memory and arithmetic time than a fixed-width machine int. Irrelevant until you "
        "are doing millions of operations.",
        security_notes="Always convert untrusted numeric input explicitly, and bound it. "
        "`int` on attacker-controlled text with a huge digit count is a CPU denial-of-service "
        "vector, because conversion is superlinear in the number of digits.",
        related=("float", "str", "round", "operators"),
        keywords=("cast", "convert", "parse number", "string to int", "truncate"),
        lesson_slugs=("variables-and-data-types",),
    ),
    ReferenceSpec(
        key="float",
        title="float()",
        kind="class",
        module="builtins",
        signature="float(x=0.0) -> float",
        summary="Convert a number or string to a binary floating-point number.",
        description="A float is a *binary* fraction, so most decimal values cannot be "
        "represented exactly. That is not a Python defect — it is IEEE 754, and every "
        "language behaves this way.",
        parameters=(
            {
                "name": "x",
                "type": "str | int | float",
                "required": False,
                "default": "0.0",
                "description": "Value to convert.",
            },
        ),
        returns="A float.",
        raises=({"error": "ValueError", "when": "The string is not a valid number."},),
        examples=(
            {"title": "From text", "code": "print(float('10.5'))", "output": "10.5"},
            {
                "title": "The classic surprise",
                "code": "print(0.1 + 0.2)\nprint(0.1 + 0.2 == 0.3)",
                "output": "0.30000000000000004\nFalse",
            },
            {
                "title": "Comparing safely",
                "code": "import math\nprint(math.isclose(0.1 + 0.2, 0.3))",
                "output": "True",
            },
        ),
        real_world_usage="Measurements, ratios, scientific quantities, anything where a "
        "tiny relative error is acceptable.",
        common_mistakes=(
            {
                "mistake": "Using float for money",
                "fix": "Store integer pence, or use decimal.Decimal. Float pennies drift, "
                "and the drift shows up in a monthly total.",
            },
            {
                "mistake": "Comparing floats with ==",
                "fix": "Use math.isclose, or compare to a tolerance.",
            },
        ),
        performance_notes="Fast — floats map onto hardware doubles. decimal.Decimal is exact "
        "but roughly two orders of magnitude slower, which is still fine for accounting "
        "volumes.",
        security_notes="Never use float for monetary or quota arithmetic where rounding could "
        "be exploited to gain fractional advantage repeatedly.",
        related=("int", "decimal.Decimal", "round"),
        keywords=("decimal", "rounding error", "ieee754", "precision", "money"),
        lesson_slugs=("variables-and-data-types",),
    ),
    ReferenceSpec(
        key="str",
        title="str()",
        kind="class",
        module="builtins",
        signature="str(object='') -> str",
        summary="The text type, and the function that converts any object to its readable form.",
        description="Python strings are immutable sequences of Unicode code points. Every "
        "method that 'changes' a string returns a new one — `s.upper()` does not modify `s`.",
        parameters=(
            {
                "name": "object",
                "type": "Any",
                "required": False,
                "default": "''",
                "description": "Object to render as text, via its __str__.",
            },
        ),
        returns="A str.",
        raises=(),
        examples=(
            {
                "title": "Immutability",
                "code": "s = 'abc'\ns.upper()\nprint(s)\nprint(s.upper())",
                "output": "abc\nABC",
            },
            {
                "title": "f-strings are the readable way to interpolate",
                "code": "name, n = 'Ada', 3\nprint(f'{name} has {n} items, {n / 7:.2f} each')",
                "output": "Ada has 3 items, 0.43 each",
            },
            {
                "title": "input() always gives you str",
                "code": "value = '5'\nprint(value + 1 if False else int(value) + 1)",
                "output": "6",
            },
        ),
        real_world_usage="Everywhere. Notably: building messages, formatting reports, and "
        "the boundary where external input arrives as text and must be converted.",
        common_mistakes=(
            {
                "mistake": "Expecting s.upper() to modify s",
                "fix": "Strings are immutable. Assign the result: s = s.upper().",
            },
            {
                "mistake": "Building a big string with += in a loop",
                "fix": "Each += copies the whole string, making the loop quadratic. Collect "
                "into a list and ''.join() once.",
            },
            {
                "mistake": "'5' + 1",
                "fix": "TypeError. Convert explicitly with int() — Python will not guess.",
            },
        ),
        performance_notes="Concatenating in a loop with += is O(n^2); str.join is O(n) and is "
        "the idiom. Strings are interned and hashed once, which is what makes them good dict "
        "keys.",
        security_notes="Never build SQL, shell commands or HTML by string interpolation of "
        "untrusted values — use parameterised queries, argument lists, and a template engine "
        "that escapes.",
        related=("str.split", "str.join", "str.strip", "int", "print"),
        keywords=("text", "string", "f-string", "format", "interpolation", "immutable"),
        lesson_slugs=("variables-and-data-types",),
    ),
    ReferenceSpec(
        key="bool",
        title="bool()",
        kind="class",
        module="builtins",
        signature="bool(x=False) -> bool",
        summary="Truth value testing — and the rules for what counts as false.",
        description="Every object is truthy unless it is explicitly falsy. The falsy set is "
        "small and worth memorising: `False`, `None`, zero of any numeric type, and every "
        "empty collection. Everything else is true.",
        parameters=(
            {
                "name": "x",
                "type": "Any",
                "required": False,
                "default": "False",
                "description": "Object to test.",
            },
        ),
        returns="True or False.",
        raises=(),
        examples=(
            {
                "title": "The falsy values",
                "code": "for value in (0, 0.0, '', [], {}, set(), None, False):\n"
                "    print(repr(value), bool(value))",
                "output": "0 False\n0.0 False\n'' False\n[] False\n{} False\nset() False\n"
                "None False\nFalse False",
            },
            {
                "title": "Idiomatic emptiness check",
                "code": "items = []\nprint('empty' if not items else 'has items')",
                "output": "empty",
            },
            {
                "title": "bool is a subclass of int",
                "code": "print(True + True, isinstance(True, int))",
                "output": "2 True",
            },
        ),
        real_world_usage="Guard clauses, default handling, and the `if not items:` idiom that "
        "replaces `if len(items) == 0:`.",
        common_mistakes=(
            {
                "mistake": "if x != None",
                "fix": "Use `if x is not None`. None is a singleton, so identity is the "
                "correct test and it cannot be fooled by a custom __eq__.",
            },
            {
                "mistake": "Treating 0 and None as interchangeable",
                "fix": "Both are falsy, but `if not count:` is true for a genuine count of "
                "zero. When zero is valid data, test `is None` explicitly.",
            },
            {
                "mistake": "if bool(x) == True",
                "fix": "Just `if x:`.",
            },
        ),
        performance_notes="Truth testing calls __bool__ or falls back to __len__, both cheap. "
        "`if not items` avoids constructing an int the way `len(items) == 0` does.",
        security_notes="",
        related=("any", "all", "isinstance", "conditionals"),
        keywords=("truthy", "falsy", "empty", "none check", "boolean"),
        lesson_slugs=("conditions",),
    ),
    ReferenceSpec(
        key="tuple",
        title="tuple()",
        kind="class",
        module="builtins",
        signature="tuple(iterable=()) -> tuple",
        summary="An immutable, ordered sequence — fixed shape, hashable, and usable as a dict key.",
        description="Reach for a tuple when the *length* carries meaning and the value will "
        "not change: a coordinate, a database row, a compound key. A list is for a variable "
        "number of the same kind of thing.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": False,
                "default": "()",
                "description": "Items to build the tuple from.",
            },
        ),
        returns="A tuple.",
        raises=(),
        examples=(
            {
                "title": "Unpacking names the positions",
                "code": "row = ('2026-01-15', 'EMEA', 4200)\ndate, region, revenue = row\n"
                "print(region, revenue)",
                "output": "EMEA 4200",
            },
            {
                "title": "The single-element comma",
                "code": "print(type((5)), type((5,)))",
                "output": "<class 'int'> <class 'tuple'>",
            },
            {
                "title": "A compound dict key",
                "code": "sales = {('EMEA', '2026-08'): 4200}\nprint(sales[('EMEA', '2026-08')])",
                "output": "4200",
            },
            {
                "title": "Immutable slots, mutable contents",
                "code": "row = (1, [2, 3])\nrow[1].append(4)\nprint(row)",
                "output": "(1, [2, 3, 4])",
            },
        ),
        real_world_usage="Database rows, multiple return values, `(region, month)` reporting "
        "keys, and `sys.version_info`.",
        common_mistakes=(
            {
                "mistake": "(x) instead of (x,)",
                "fix": "Parentheses group; the comma makes the tuple. This bites in test "
                "parameter lists.",
            },
            {
                "mistake": "Assuming any tuple is hashable",
                "fix": "Only if everything inside is. A tuple containing a list cannot be a "
                "dict key.",
            },
            {
                "mistake": "Using a 6-field tuple as a record",
                "fix": "row[4] tells the reader nothing. Use typing.NamedTuple or a dataclass.",
            },
        ),
        performance_notes="Slightly smaller and faster to construct than a list, because the "
        "size is fixed. Choose on meaning, not on speed — except when you need a hashable "
        "compound key, where a tuple gives O(1) dict lookup.",
        security_notes="A module-level tuple of constants cannot be mutated by a caller the "
        "way a list can. That is defensive, not a security boundary.",
        related=("list", "set", "zip", "enumerate", "dataclasses.dataclass"),
        keywords=("immutable", "unpacking", "fixed shape", "record", "hashable", "dict key"),
        lesson_slugs=("tuples-and-unpacking",),
    ),
    ReferenceSpec(
        key="list",
        title="list()",
        kind="class",
        module="builtins",
        signature="list(iterable=()) -> list",
        summary="A mutable, ordered sequence — the default collection, and a poor queue.",
        description="Backed by a contiguous array of references. That makes indexing and "
        "appending fast, and anything involving the *front* slow, because every later element "
        "has to shift.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": False,
                "default": "()",
                "description": "Items to build the list from.",
            },
        ),
        returns="A list.",
        raises=(),
        examples=(
            {
                "title": "Aliasing is not copying",
                "code": "a = [1, 2]\nb = a\nb.append(3)\nprint(a)",
                "output": "[1, 2, 3]",
            },
            {
                "title": "Copying",
                "code": "a = [1, 2]\nb = a[:]\nb.append(3)\nprint(a, b)",
                "output": "[1, 2] [1, 2, 3]",
            },
            {
                "title": "Membership is a scan",
                "code": "print(3 in [1, 2, 3])",
                "output": "True",
            },
        ),
        real_world_usage="Almost every ordered collection: rows read from a file, results "
        "accumulated in a loop, a stack.",
        common_mistakes=(
            {
                "mistake": "Using a list as a queue with pop(0)",
                "fix": "pop(0) is O(n), so draining is O(n^2). Use collections.deque.",
            },
            {
                "mistake": "`x in big_list` inside a loop",
                "fix": "That is O(n*m). Build a set once and test against it.",
            },
            {
                "mistake": "A mutable default argument: def f(items=[])",
                "fix": "The list is created once and shared between calls. Use None and "
                "create inside.",
            },
            {
                "mistake": "Removing items while iterating",
                "fix": "The index shifts and elements get skipped. Iterate a copy, or build "
                "a new list.",
            },
        ),
        performance_notes="Index O(1); append amortised O(1); `in`, insert(0) and pop(0) all "
        "O(n). Those last three are the source of most accidental quadratic behaviour.",
        security_notes="Unbounded appends from untrusted input are a memory-exhaustion vector. "
        "Bound the size explicitly.",
        related=("tuple", "set", "list.append", "list.pop", "list.sort", "collections.deque"),
        keywords=("array", "mutable", "sequence", "aliasing", "copy", "queue"),
        lesson_slugs=("lists", "complexity-and-structure-choice"),
    ),
    ReferenceSpec(
        key="dict",
        title="dict()",
        kind="class",
        module="builtins",
        signature="dict(**kwargs) | dict(mapping) | dict(iterable_of_pairs) -> dict",
        summary="A hash map from hashable keys to values, with O(1) lookup and insertion "
        "order preserved.",
        description="The workhorse of Python. Since 3.7 insertion order is guaranteed by the "
        "language, not merely an implementation detail — which is what makes "
        "`dict.fromkeys` the order-preserving way to deduplicate.",
        parameters=(
            {
                "name": "mapping / iterable / kwargs",
                "type": "Mapping | Iterable[tuple] | Any",
                "required": False,
                "description": "Initial contents.",
            },
        ),
        returns="A dict.",
        raises=({"error": "TypeError", "when": "A key is unhashable, such as a list."},),
        examples=(
            {
                "title": "Three ways to build one",
                "code": "print(dict(a=1), dict([('a', 1)]), {'a': 1})",
                "output": "{'a': 1} {'a': 1} {'a': 1}",
            },
            {
                "title": "Order-preserving deduplication",
                "code": "print(list(dict.fromkeys([3, 1, 3, 2])))",
                "output": "[3, 1, 2]",
            },
            {
                "title": "Merging, right wins",
                "code": "print({'a': 1, 'b': 2} | {'b': 9})",
                "output": "{'a': 1, 'b': 9}",
            },
        ),
        real_world_usage="Parsed JSON, configuration, lookup indexes, counting, and grouping "
        "records by a key.",
        common_mistakes=(
            {
                "mistake": "d[key] for an optional field",
                "fix": "Use d.get(key, default) when absence is expected. Keep d[key] for "
                "when absence is a bug you want reported.",
            },
            {
                "mistake": "Using a list as a key",
                "fix": "Keys must be hashable. Convert to a tuple.",
            },
            {
                "mistake": "Mutating a dict while iterating it",
                "fix": "RuntimeError. Iterate over list(d) or build a new dict.",
            },
        ),
        performance_notes="Lookup, insert and delete are O(1) average. Memory overhead is "
        "real — roughly 2–3x the payload — so a million small dicts is worth replacing with "
        "dataclasses with __slots__ or NamedTuples.",
        security_notes="Building dicts from untrusted keys is a memory vector, and pathological "
        "key sets can degrade hashing. Bound the number of distinct keys you will accept.",
        related=("dict.get", "dict.items", "dict.setdefault", "set", "collections.defaultdict"),
        keywords=("hash map", "mapping", "lookup", "json object", "ordered", "fromkeys"),
        lesson_slugs=("dictionaries", "complexity-and-structure-choice"),
    ),
    ReferenceSpec(
        key="set",
        title="set()",
        kind="class",
        module="builtins",
        signature="set(iterable=()) -> set",
        summary="An unordered collection of unique hashable items, with O(1) membership and "
        "the set operators.",
        description="Two questions a list answers badly: *is this in there?* and *how do "
        "these two collections relate?* A set answers the first in constant time and the "
        "second with an operator.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": False,
                "default": "()",
                "description": "Items to build the set from; duplicates collapse.",
            },
        ),
        returns="A set.",
        raises=({"error": "TypeError", "when": "An item is unhashable, such as a list."},),
        examples=(
            {
                "title": "Set algebra",
                "code": "a, b = {1, 2, 3}, {3, 4}\n"
                "print(sorted(a | b), sorted(a & b), sorted(a - b), sorted(a ^ b))",
                "output": "[1, 2, 3, 4] [3] [1, 2] [1, 2, 4]",
            },
            {
                "title": "The empty-set trap",
                "code": "print(type({}), type(set()))",
                "output": "<class 'dict'> <class 'set'>",
            },
            {
                "title": "Membership does not scan",
                "code": "banned = {'u1', 'u2'}\nprint('u1' in banned)",
                "output": "True",
            },
        ),
        real_world_usage="Permission checks (`required - granted` is what is missing), "
        "deduplicating IDs, tracking visited nodes so a crawler terminates.",
        common_mistakes=(
            {
                "mistake": "{} for an empty set",
                "fix": "That is a dict. Use set().",
            },
            {
                "mistake": "list(set(items)) to dedupe when order matters",
                "fix": "Sets are unordered. Use list(dict.fromkeys(items)).",
            },
            {
                "mistake": "s = s.add(x)",
                "fix": "add() mutates in place and returns None, so this destroys the set.",
            },
            {
                "mistake": "Relying on iteration order",
                "fix": "It is an implementation detail. Sort when you need determinism.",
            },
        ),
        performance_notes="Membership, add and discard are O(1) average; union, intersection "
        "and difference are linear in the inputs. Building a set is O(n), so it pays off when "
        "you test membership more than once or twice.",
        security_notes="The right structure for allowlists, because the check is one "
        "unambiguous operation rather than a loop that can be subtly wrong. Bound the size "
        "when built from untrusted input.",
        related=("frozenset", "dict", "list", "collections.Counter"),
        keywords=("unique", "dedupe", "membership", "union", "intersection", "difference"),
        lesson_slugs=("sets-and-membership",),
    ),
    ReferenceSpec(
        key="frozenset",
        title="frozenset()",
        kind="class",
        module="builtins",
        signature="frozenset(iterable=()) -> frozenset",
        summary="An immutable set — so it is hashable, and can itself be a dict key or set member.",
        description="Everything a set does except mutate. Its reason to exist is hashability: "
        "a set cannot be a dict key, a frozenset can.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": False,
                "default": "()",
                "description": "Items to freeze.",
            },
        ),
        returns="A frozenset.",
        raises=(),
        examples=(
            {
                "title": "A set of sets needs frozensets",
                "code": "groups = {frozenset({'read'}), frozenset({'read', 'write'})}\n"
                "print(len(groups))",
                "output": "2",
            },
            {
                "title": "Caching by an unordered key",
                "code": "cache = {frozenset({'a', 'b'}): 'result'}\n"
                "print(cache[frozenset({'b', 'a'})])",
                "output": "result",
            },
            {
                "title": "No mutation",
                "code": "frozenset({1}).add(2)",
                "output": "AttributeError: 'frozenset' object has no attribute 'add'",
            },
        ),
        real_world_usage="Permission-set keys, memoising a function whose argument is an "
        "unordered collection, module-level constant sets that callers must not mutate.",
        common_mistakes=(
            {
                "mistake": "Expecting frozenset to be deeply immutable",
                "fix": "It cannot gain or lose members, but it can only contain hashable "
                "items in the first place, so this rarely bites.",
            },
            {
                "mistake": "Using frozenset where a tuple is meant",
                "fix": "A frozenset has no order and no duplicates. If order matters, you "
                "want a tuple.",
            },
        ),
        performance_notes="Same complexity as set. Hashing is computed once and cached, so "
        "repeated dict lookups with the same frozenset key are cheap.",
        security_notes="Useful for constants that must not be mutated by untrusted callers.",
        related=("set", "tuple", "dict"),
        keywords=("immutable set", "hashable", "constant", "dict key"),
        lesson_slugs=("sets-and-membership",),
    ),
)

BUILTIN_FUNCTIONS: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        key="sorted",
        title="sorted()",
        kind="function",
        module="builtins",
        signature="sorted(iterable, *, key=None, reverse=False) -> list",
        summary="Return a new sorted list from any iterable, leaving the input untouched.",
        description="The counterpart to `list.sort()`, which sorts in place and returns None. "
        "`key` is a function mapping each element to the value actually compared, and is "
        "called **once per element** rather than once per comparison.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": True,
                "description": "Anything iterable, not just a list.",
            },
            {
                "name": "key",
                "type": "Callable",
                "required": False,
                "default": "None",
                "description": "Extracts the value to order by.",
            },
            {
                "name": "reverse",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Descending when True.",
            },
        ),
        returns="A new list.",
        raises=(
            {
                "error": "TypeError",
                "when": "Elements are not mutually comparable, e.g. mixing str and int.",
            },
        ),
        examples=(
            {
                "title": "A key function",
                "code": "print(sorted(['banana', 'kiwi', 'apple'], key=len))",
                "output": "['kiwi', 'apple', 'banana']",
            },
            {
                "title": "A tuple key sorts by several fields",
                "code": "rows = [('b', 2), ('a', 2), ('c', 1)]\n"
                "print(sorted(rows, key=lambda r: (r[1], r[0])))",
                "output": "[('c', 1), ('a', 2), ('b', 2)]",
            },
            {
                "title": "Descending one field, ascending another",
                "code": "people = [{'n': 'Ada', 's': 91}, {'n': 'Alan', 's': 78}]\n"
                "print([p['n'] for p in sorted(people, key=lambda p: (-p['s'], p['n']))])",
                "output": "['Ada', 'Alan']",
            },
        ),
        real_world_usage="Leaderboards, log lines by timestamp, and giving API responses a "
        "deterministic order so pagination is stable and tests are not flaky.",
        common_mistakes=(
            {
                "mistake": "key=len()",
                "fix": "Pass the function itself: key=len. Calling it invokes len with no "
                "arguments.",
            },
            {
                "mistake": "Trying to negate a string to reverse it",
                "fix": "Only numbers can be negated. Do two stable sorts instead — least "
                "significant field first.",
            },
            {
                "mistake": "reversed(sorted(xs)) instead of sorted(xs, reverse=True)",
                "fix": "They differ when keys tie: reverse=True preserves the original order "
                "of equal elements, reversing afterwards flips it.",
            },
        ),
        performance_notes="Timsort: O(n log n) worst case, approaching O(n) on nearly sorted "
        "data, and stable. The key function costs O(n) calls. If you only need the extremes, "
        "min, max or heapq.nlargest are O(n).",
        security_notes="Do not sort by a user-supplied field name passed to getattr — validate "
        "against an allowlist. Unbounded sorts of untrusted input are a CPU and memory vector.",
        related=("list.sort", "min", "max", "heapq.nlargest", "operators"),
        keywords=("sort", "order", "key function", "stable", "descending", "multi-field"),
        lesson_slugs=("sorting-and-keys", "comprehensions-in-depth", "stacks-queues-heaps"),
    ),
    ReferenceSpec(
        key="len",
        title="len()",
        kind="function",
        module="builtins",
        signature="len(obj) -> int",
        summary="The number of items in a container, in O(1) for every builtin.",
        description="Calls the object's `__len__`. Builtin containers store their length, so "
        "this never walks the collection.",
        parameters=(
            {
                "name": "obj",
                "type": "Sized",
                "required": True,
                "description": "Anything implementing __len__.",
            },
        ),
        returns="A non-negative int.",
        raises=(
            {
                "error": "TypeError",
                "when": "The object has no __len__ — a generator, for instance.",
            },
        ),
        examples=(
            {
                "title": "Containers",
                "code": "print(len('abc'), len([1, 2]), len({'a': 1}), len({1, 2, 3}))",
                "output": "3 2 1 3",
            },
            {
                "title": "Generators have no length",
                "code": "len(x for x in range(3))",
                "output": "TypeError: object of type 'generator' has no len()",
            },
            {
                "title": "Counting a generator means consuming it",
                "code": "print(sum(1 for _ in range(3)))",
                "output": "3",
            },
        ),
        real_world_usage="Validation bounds, progress reporting, and deciding whether to take "
        "a fast path.",
        common_mistakes=(
            {
                "mistake": "if len(items) == 0",
                "fix": "`if not items:` is the idiom and does not build an int.",
            },
            {
                "mistake": "len() on a generator or file object",
                "fix": "Neither knows its length. Materialise with list() if you can afford "
                "the memory, or count as you go.",
            },
            {
                "mistake": "len() of a Unicode string as a display width",
                "fix": "It counts code points, not glyphs. An emoji or combining accent can "
                "be several code points.",
            },
        ),
        performance_notes="O(1) for every builtin container. A custom __len__ can be as slow "
        "as its author made it.",
        security_notes="Check length *before* processing untrusted input, not after.",
        related=("bool", "sum", "range"),
        keywords=("length", "size", "count", "empty"),
        lesson_slugs=("functions",),
    ),
    ReferenceSpec(
        key="sum",
        title="sum()",
        kind="function",
        module="builtins",
        signature="sum(iterable, /, start=0)",
        summary="Add up an iterable of numbers, starting from `start`.",
        description="Takes any iterable, including a generator expression — which is how you "
        "total a large dataset without building a list of it.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable[int | float]",
                "required": True,
                "description": "Numbers to add.",
            },
            {
                "name": "start",
                "type": "int | float",
                "required": False,
                "default": "0",
                "description": "Initial value, and what an empty iterable returns.",
            },
        ),
        returns="The total.",
        raises=({"error": "TypeError", "when": "An element is not addable to the running total."},),
        examples=(
            {"title": "Basic", "code": "print(sum([1, 2, 3]))", "output": "6"},
            {
                "title": "A generator expression keeps memory flat",
                "code": "print(sum(x * x for x in range(1_000_000)))",
                "output": "333332833333500000",
            },
            {
                "title": "Counting with a condition",
                "code": "words = ['a', 'bb', 'ccc']\nprint(sum(1 for w in words if len(w) > 1))",
                "output": "2",
            },
            {
                "title": "Empty is start, not an error",
                "code": "print(sum([]))",
                "output": "0",
            },
        ),
        real_world_usage="Totalling money in integer pence, counting matches, aggregating "
        "report columns.",
        common_mistakes=(
            {
                "mistake": "sum() to concatenate lists",
                "fix": "It is quadratic. Use itertools.chain.from_iterable or a comprehension.",
            },
            {
                "mistake": "Summing floats for money",
                "fix": "Errors accumulate. Sum integer pence, or use Decimal.",
            },
            {
                "mistake": "sum(a_generator) then len(a_generator)",
                "fix": "The generator is exhausted by the first pass and the second sees nothing.",
            },
        ),
        performance_notes="O(n) with a small constant. `math.fsum` is slower but keeps float "
        "precision when summing many values of differing magnitude.",
        security_notes="",
        related=("len", "range", "min", "max"),
        keywords=("total", "add", "aggregate", "reduce", "count"),
        lesson_slugs=("loops", "functions"),
    ),
    ReferenceSpec(
        key="range",
        title="range()",
        kind="class",
        module="builtins",
        signature="range(stop) | range(start, stop, step) -> range",
        summary="A lazy arithmetic sequence — memory-flat regardless of size, and the "
        "standard way to loop a fixed number of times.",
        description="`range` is not a list. It stores start, stop and step, and computes each "
        "value on demand, so `range(10 ** 9)` is instant and costs nothing.",
        parameters=(
            {
                "name": "start",
                "type": "int",
                "required": False,
                "default": "0",
                "description": "First value, inclusive.",
            },
            {
                "name": "stop",
                "type": "int",
                "required": True,
                "description": "Upper bound, exclusive.",
            },
            {
                "name": "step",
                "type": "int",
                "required": False,
                "default": "1",
                "description": "Increment; may be negative.",
            },
        ),
        returns="A range object, iterable and indexable.",
        raises=({"error": "ValueError", "when": "step is zero."},),
        examples=(
            {
                "title": "Exclusive upper bound",
                "code": "print(list(range(3)))",
                "output": "[0, 1, 2]",
            },
            {
                "title": "Start, stop, step",
                "code": "print(list(range(2, 11, 3)))",
                "output": "[2, 5, 8]",
            },
            {
                "title": "Counting down",
                "code": "print(list(range(3, 0, -1)))",
                "output": "[3, 2, 1]",
            },
            {
                "title": "Lazy, so size is free",
                "code": "print(len(range(10 ** 9)))",
                "output": "1000000000",
            },
        ),
        real_world_usage="Repeating an action n times, generating test data, and paging "
        "through offsets in fixed steps.",
        common_mistakes=(
            {
                "mistake": "Expecting range(1, 5) to include 5",
                "fix": "The stop is exclusive. This is what makes range(len(x)) line up with "
                "valid indices.",
            },
            {
                "mistake": "for i in range(len(items)): items[i]",
                "fix": "Iterate the items directly, or use enumerate when you need the index too.",
            },
            {
                "mistake": "Treating range as a list",
                "fix": "It has no append and is not a list. Wrap in list() if you truly need one.",
            },
        ),
        performance_notes="O(1) memory and construction whatever the size. Membership "
        "(`x in range(...)`) is O(1) too, because it is arithmetic rather than a scan.",
        security_notes="Never build a range from an unbounded untrusted integer and "
        "materialise it — `list(range(n))` with attacker-controlled n is memory exhaustion.",
        related=("enumerate", "len", "sum", "list"),
        keywords=("loop", "iterate", "count", "sequence", "lazy", "step"),
        lesson_slugs=("loops",),
    ),
    ReferenceSpec(
        key="any",
        title="any()",
        kind="function",
        module="builtins",
        signature="any(iterable) -> bool",
        summary="True if at least one element is truthy — short-circuiting on the first hit.",
        description="Pairs with `all`. Both stop as soon as the answer is known, so passing a "
        "generator expression means you may not evaluate the whole sequence.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": True,
                "description": "Values or conditions to test.",
            },
        ),
        returns="True or False. False for an empty iterable.",
        raises=(),
        examples=(
            {
                "title": "With a generator expression",
                "code": "rows = [{'error': None}, {'error': 'timeout'}]\n"
                "print(any(r['error'] for r in rows))",
                "output": "True",
            },
            {
                "title": "Empty is False",
                "code": "print(any([]))",
                "output": "False",
            },
            {
                "title": "It short-circuits",
                "code": "def check(n):\n    print('checked', n)\n    return n > 1\n\n"
                "print(any(check(n) for n in [1, 2, 3]))",
                "output": "checked 1\nchecked 2\nTrue",
            },
        ),
        real_world_usage="Validation ('did anything fail?'), permission checks, and replacing "
        "a loop with a flag variable.",
        common_mistakes=(
            {
                "mistake": "any([expensive(x) for x in xs])",
                "fix": "The list comprehension evaluates everything first, defeating the "
                "short circuit. Drop the brackets to pass a generator.",
            },
            {
                "mistake": "Expecting any() to return the matching element",
                "fix": "It returns a bool. Use next((x for x in xs if cond(x)), None) for the "
                "element.",
            },
        ),
        performance_notes="O(n) worst case, often much less thanks to short-circuiting — "
        "provided you pass a lazy iterable.",
        security_notes="",
        related=("all", "bool", "next"),
        keywords=("exists", "at least one", "short circuit", "validation"),
        lesson_slugs=("conditions",),
    ),
    ReferenceSpec(
        key="all",
        title="all()",
        kind="function",
        module="builtins",
        signature="all(iterable) -> bool",
        summary="True if every element is truthy — and, notably, True for an empty iterable.",
        description="The empty case surprises people and is correct: 'every element satisfies "
        "this' is vacuously true when there are no elements. If empty should fail, test that "
        "separately.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": True,
                "description": "Values or conditions to test.",
            },
        ),
        returns="True or False. True for an empty iterable.",
        raises=(),
        examples=(
            {
                "title": "Validating every row",
                "code": "rows = [{'id': 1}, {'id': 2}]\nprint(all(r.get('id') for r in rows))",
                "output": "True",
            },
            {
                "title": "The empty surprise",
                "code": "print(all([]))",
                "output": "True",
            },
            {
                "title": "Requiring non-empty as well",
                "code": "rows = []\nprint(bool(rows) and all(r.get('id') for r in rows))",
                "output": "False",
            },
        ),
        real_world_usage="Pre-flight checks, asserting every record has a required field, "
        "confirming all migrations applied.",
        common_mistakes=(
            {
                "mistake": "Assuming all([]) is False",
                "fix": "It is True. Add an explicit emptiness check when that matters — this "
                "is a real source of validation that silently passes on no data.",
            },
            {
                "mistake": "all([f(x) for x in xs])",
                "fix": "Pass a generator so the short circuit works.",
            },
        ),
        performance_notes="O(n) worst case, short-circuiting on the first falsy value.",
        security_notes="A validator built on `all` over an empty input passes. If the input "
        "should never be empty, check that first — otherwise an attacker who can make the "
        "collection empty bypasses validation.",
        related=("any", "bool"),
        keywords=("every", "all true", "vacuous truth", "validation", "short circuit"),
        lesson_slugs=("conditions",),
    ),
    ReferenceSpec(
        key="isinstance",
        title="isinstance()",
        kind="function",
        module="builtins",
        signature="isinstance(obj, class_or_tuple) -> bool",
        summary="Is this object an instance of that class, or of any class in that tuple — "
        "subclasses included.",
        description="The correct runtime type check, because it respects inheritance where "
        "`type(x) == C` does not. Use it at boundaries, not as a substitute for polymorphism.",
        parameters=(
            {"name": "obj", "type": "Any", "required": True, "description": "Object to test."},
            {
                "name": "class_or_tuple",
                "type": "type | tuple[type, ...]",
                "required": True,
                "description": "A class, or a tuple of classes to test against.",
            },
        ),
        returns="True or False.",
        raises=(
            {"error": "TypeError", "when": "The second argument is not a type or tuple of types."},
        ),
        examples=(
            {
                "title": "Several types at once",
                "code": "print(isinstance(3, (int, float)), isinstance('a', (int, float)))",
                "output": "True False",
            },
            {
                "title": "The bool trap",
                "code": "print(isinstance(True, int))",
                "output": "True",
            },
            {
                "title": "Subclasses count",
                "code": "class Base: pass\nclass Child(Base): pass\n"
                "print(isinstance(Child(), Base), type(Child()) == Base)",
                "output": "True False",
            },
        ),
        real_world_usage="Validating deserialised JSON, writing a function that accepts either "
        "a path or a string, and guarding a public API boundary.",
        common_mistakes=(
            {
                "mistake": "isinstance(x, int) to exclude booleans",
                "fix": "bool subclasses int, so True passes. Test `type(x) is int`, or check "
                "`not isinstance(x, bool)` as well.",
            },
            {
                "mistake": "isinstance chains instead of polymorphism",
                "fix": "A long elif ladder on type usually wants a method on each class, or "
                "a dict dispatch.",
            },
            {
                "mistake": "type(x) == C",
                "fix": "Rejects subclasses, which is almost never what you want.",
            },
        ),
        performance_notes="Very fast, and cheaper than a try/except in the failing case. "
        "Prefer duck typing in hot loops where any check is overhead.",
        security_notes="Type-check untrusted deserialised data before use. A JSON field you "
        "assume is a string may arrive as a dict and reach code that cannot handle it.",
        related=("bool", "property", "type"),
        keywords=("type check", "instance", "subclass", "validation", "duck typing"),
        lesson_slugs=("object-oriented-programming",),
    ),
    ReferenceSpec(
        key="property",
        title="property()",
        kind="decorator",
        module="builtins",
        signature="@property",
        summary="Expose a method as an attribute, so a computed value reads like stored state.",
        description="Lets you start with a plain attribute and add validation or computation "
        "later without changing a single caller. That is its real purpose: it removes the "
        "reason to write Java-style getters up front.",
        parameters=(),
        returns="A descriptor which, on an instance, calls the method on attribute access.",
        raises=(
            {
                "error": "AttributeError",
                "when": "Assigning to a property with no setter defined.",
            },
        ),
        examples=(
            {
                "title": "A computed attribute",
                "code": "class Order:\n    def __init__(self, unit_pence, qty):\n"
                "        self.unit_pence, self.qty = unit_pence, qty\n\n"
                "    @property\n    def total_pence(self):\n"
                "        return self.unit_pence * self.qty\n\n"
                "print(Order(1050, 3).total_pence)",
                "output": "3150",
            },
            {
                "title": "Validation on assignment",
                "code": "class Item:\n    @property\n    def qty(self):\n"
                "        return self._qty\n\n    @qty.setter\n    def qty(self, value):\n"
                "        if value < 0:\n            raise ValueError('qty must be >= 0')\n"
                "        self._qty = value\n\n"
                "i = Item()\ni.qty = 5\nprint(i.qty)",
                "output": "5",
            },
            {
                "title": "Read-only by default",
                "code": "class C:\n    @property\n    def x(self):\n        return 1\n\nC().x = 2",
                "output": "AttributeError: property 'x' of 'C' object has no setter",
            },
        ),
        real_world_usage="Derived totals, lazily loaded relations, validated fields, and "
        "keeping a computed value from drifting out of sync with its inputs.",
        common_mistakes=(
            {
                "mistake": "Expensive work inside a property",
                "fix": "Callers assume attribute access is cheap. If it does I/O, make it a "
                "method so the cost is visible at the call site.",
            },
            {
                "mistake": "Recursion via self.x inside the property named x",
                "fix": "Store the backing value under a different name, such as self._x.",
            },
            {
                "mistake": "Adding a property with a setter that does nothing but assign",
                "fix": "Then it earns nothing. Use a plain attribute until you need the behaviour.",
            },
        ),
        performance_notes="Attribute access through a property is noticeably slower than a "
        "plain attribute, because it is a function call. Irrelevant except in hot loops.",
        security_notes="A setter is a good place to validate, but it is not a boundary — "
        "callers can reach the backing attribute directly.",
        related=("dataclasses.dataclass", "isinstance"),
        keywords=("getter", "setter", "computed attribute", "validation", "encapsulation"),
        lesson_slugs=("object-oriented-programming",),
    ),
)

ERRORS: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        key="try",
        title="try / except / else / finally",
        kind="statement",
        module="builtins",
        signature="try: ... except SomeError as exc: ... else: ... finally: ...",
        summary="Handle a failure you anticipated, as narrowly as you can, as close to the "
        "cause as you can.",
        description="The four clauses have distinct jobs. `except` handles a failure; `else` "
        "runs only when nothing was raised, keeping the success path out of the protected "
        "block; `finally` always runs, for cleanup.",
        parameters=(),
        returns="Nothing; a control-flow statement.",
        raises=(),
        examples=(
            {
                "title": "Narrow, with the cause bound",
                "code": "try:\n    value = int('abc')\nexcept ValueError as exc:\n"
                "    print('bad input:', exc)",
                "output": "bad input: invalid literal for int() with base 10: 'abc'",
            },
            {
                "title": "else keeps the success path out of the try",
                "code": "try:\n    n = int('42')\nexcept ValueError:\n    print('bad')\n"
                "else:\n    print('parsed', n)",
                "output": "parsed 42",
            },
            {
                "title": "finally runs either way",
                "code": "try:\n    raise RuntimeError('boom')\nexcept RuntimeError:\n"
                "    print('handled')\nfinally:\n    print('cleanup')",
                "output": "handled\ncleanup",
            },
            {
                "title": "Preserving the cause when re-raising",
                "code": "try:\n    try:\n        int('x')\n    except ValueError as exc:\n"
                "        raise RuntimeError('config invalid') from exc\n"
                "except RuntimeError as exc:\n    print(exc, '| caused by', type(exc.__cause__).__name__)",
                "output": "config invalid | caused by ValueError",
            },
        ),
        real_world_usage="Parsing external input, network calls, file access, and any "
        "boundary where the failure is expected and recoverable.",
        common_mistakes=(
            {
                "mistake": "except: or except Exception:",
                "fix": "Swallows typos, KeyboardInterrupt and genuine bugs. Catch the "
                "specific error you can handle.",
            },
            {
                "mistake": "A large try block",
                "fix": "You no longer know which statement raised. Wrap the single risky "
                "call; put the rest in else.",
            },
            {
                "mistake": "except ... : pass",
                "fix": "Silent failure is the hardest kind to debug. At minimum, log it.",
            },
            {
                "mistake": "raise NewError(str(exc))",
                "fix": "Use `raise NewError(...) from exc` so the original traceback survives.",
            },
            {
                "mistake": "return inside finally",
                "fix": "It discards an in-flight exception, silently swallowing the failure.",
            },
        ),
        performance_notes="Entering a try block is essentially free in modern CPython; raising "
        "and catching is not. 'Easier to ask forgiveness' is fine for the rare case and wrong "
        "for the common one.",
        security_notes="Never let an exception message reach an end user verbatim — tracebacks "
        "and database errors leak paths, queries and schema. Log the detail, return something "
        "generic.",
        related=("Exception", "ValueError", "pytest.raises"),
        keywords=("exception", "error handling", "catch", "finally", "raise from", "cleanup"),
        lesson_slugs=("exceptions",),
    ),
    ReferenceSpec(
        key="Exception",
        title="Exception",
        kind="class",
        module="builtins",
        signature="class Exception(BaseException)",
        summary="The base class for every error you should normally catch — and the one to "
        "subclass for your own.",
        description="`BaseException` sits above it and includes `KeyboardInterrupt` and "
        "`SystemExit`, which is exactly why you catch `Exception` and not `BaseException`: "
        "Ctrl-C should not be swallowed by your retry loop.",
        parameters=(
            {
                "name": "*args",
                "type": "Any",
                "required": False,
                "description": "Usually a single message string.",
            },
        ),
        returns="An exception instance.",
        raises=(),
        examples=(
            {
                "title": "A domain-specific hierarchy",
                "code": "class BillingError(Exception):\n    pass\n\n"
                "class CardDeclined(BillingError):\n    def __init__(self, code):\n"
                "        super().__init__(f'declined: {code}')\n        self.code = code\n\n"
                "try:\n    raise CardDeclined('51')\nexcept BillingError as exc:\n"
                "    print(exc, exc.code)",
                "output": "declined: 51 51",
            },
            {
                "title": "Catching several kinds",
                "code": "try:\n    raise KeyError('missing')\nexcept (KeyError, ValueError) as exc:\n"
                "    print(type(exc).__name__)",
                "output": "KeyError",
            },
        ),
        real_world_usage="A base error per subsystem lets callers catch everything from your "
        "library with one except, while still distinguishing specific failures.",
        common_mistakes=(
            {
                "mistake": "Subclassing BaseException",
                "fix": "Almost always wrong. Subclass Exception so ordinary handlers see it.",
            },
            {
                "mistake": "Raising a bare Exception('...')",
                "fix": "Callers cannot distinguish it from anything else. Define a specific class.",
            },
            {
                "mistake": "Attaching no data",
                "fix": "Carry the status, the id, the offending value — whatever a handler "
                "needs to react rather than just log.",
            },
        ),
        performance_notes="Defining exception classes is free. Raising costs a traceback, so "
        "do not use exceptions for ordinary control flow in a hot loop.",
        security_notes="Do not put secrets in exception messages — they reach logs, error "
        "trackers and sometimes HTTP responses.",
        related=("try", "ValueError", "pytest.raises"),
        keywords=("error", "custom exception", "hierarchy", "baseexception", "raise"),
        lesson_slugs=("exceptions",),
    ),
    ReferenceSpec(
        key="ValueError",
        title="ValueError",
        kind="class",
        module="builtins",
        signature="class ValueError(Exception)",
        summary="The right type, but a value that makes no sense — the standard error for "
        "failed validation and parsing.",
        description="Contrast with `TypeError`, which means the wrong *kind* of thing. "
        "`int('abc')` is a ValueError: str is an acceptable argument type, 'abc' is not an "
        "acceptable value.",
        parameters=(
            {
                "name": "*args",
                "type": "Any",
                "required": False,
                "description": "Usually a message explaining what was expected.",
            },
        ),
        returns="An exception instance.",
        raises=(),
        examples=(
            {
                "title": "Where it comes from",
                "code": "for call in (lambda: int('abc'), lambda: [1].index(9)):\n"
                "    try:\n        call()\n    except ValueError as exc:\n"
                "        print(type(exc).__name__, '-', exc)",
                "output": "ValueError - invalid literal for int() with base 10: 'abc'\n"
                "ValueError - 9 is not in list",
            },
            {
                "title": "Raising it from your own validation",
                "code": "def set_qty(n):\n    if n < 0:\n"
                "        raise ValueError(f'qty must be >= 0, got {n}')\n    return n\n\n"
                "try:\n    set_qty(-1)\nexcept ValueError as exc:\n    print(exc)",
                "output": "qty must be >= 0, got -1",
            },
        ),
        real_world_usage="Validating function arguments, parsing user input, and rejecting a "
        "malformed record at the boundary rather than deep inside.",
        common_mistakes=(
            {
                "mistake": "Raising TypeError for a bad value",
                "fix": "TypeError is for the wrong type. A negative quantity is a ValueError.",
            },
            {
                "mistake": "A message with no context",
                "fix": "Include what was expected and what arrived. 'invalid input' costs the "
                "next debugger an hour.",
            },
            {
                "mistake": "Catching ValueError around a whole block",
                "fix": "You lose which conversion failed. Wrap the single call.",
            },
        ),
        performance_notes="",
        security_notes="Validation messages are shown to users more often than any other "
        "error, so keep them descriptive about the *input contract* and silent about internals.",
        related=("try", "Exception", "int", "float"),
        keywords=("validation", "invalid value", "parse error", "typeerror", "argument"),
        lesson_slugs=("exceptions",),
    ),
)

CONTAINERS: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        key="dict.items",
        title="dict.items()",
        kind="method",
        module="builtins",
        signature="dict.items() -> ItemsView[tuple[K, V]]",
        summary="A live view of (key, value) pairs — the idiomatic way to iterate a dict.",
        description="A *view*, not a copy: it reflects later changes to the dict and costs "
        "O(1) to create. That is also why mutating the dict while iterating a view raises.",
        parameters=(),
        returns="An ItemsView, iterable and set-like.",
        raises=(
            {
                "error": "RuntimeError",
                "when": "The dict changes size during iteration.",
            },
        ),
        examples=(
            {
                "title": "Unpack in the for target",
                "code": "totals = {'EMEA': 4200, 'APAC': 3100}\n"
                "for region, revenue in totals.items():\n    print(region, revenue)",
                "output": "EMEA 4200\nAPAC 3100",
            },
            {
                "title": "It is a live view",
                "code": "d = {'a': 1}\nview = d.items()\nd['b'] = 2\nprint(list(view))",
                "output": "[('a', 1), ('b', 2)]",
            },
            {
                "title": "Sorting by value",
                "code": "d = {'a': 3, 'b': 1}\nprint(sorted(d.items(), key=lambda kv: kv[1]))",
                "output": "[('b', 1), ('a', 3)]",
            },
            {
                "title": "Mutating during iteration",
                "code": "d = {'a': 1}\nfor k in d:\n    d['b'] = 2",
                "output": "RuntimeError: dictionary changed size during iteration",
            },
        ),
        real_world_usage="Rendering a mapping into a report, inverting a dict, and building "
        "sorted output from an aggregation.",
        common_mistakes=(
            {
                "mistake": "for k in d: v = d[k]",
                "fix": "That is a second lookup per key. Use .items().",
            },
            {
                "mistake": "Adding or removing keys while iterating",
                "fix": "Iterate over list(d.items()) if you must change the dict.",
            },
            {
                "mistake": "Expecting .items() to be a list",
                "fix": "It is a view — no indexing. Wrap in list() if you need that.",
            },
        ),
        performance_notes="O(1) to create, O(n) to iterate, no copy. `list(d.items())` does "
        "copy and is O(n) memory.",
        security_notes="",
        related=("dict", "dict.get", "dict.setdefault", "sorted"),
        keywords=("iterate dict", "key value pairs", "view", "unpack"),
        lesson_slugs=("dictionaries",),
    ),
    ReferenceSpec(
        key="dict.setdefault",
        title="dict.setdefault()",
        kind="method",
        module="builtins",
        signature="dict.setdefault(key, default=None) -> V",
        summary="Return the value at `key`, inserting `default` first if the key is absent.",
        description="The difference from `.get` is the insertion: `.get` never modifies the "
        "dict, `setdefault` does. That is what makes it work for grouping, where you need the "
        "container you just defaulted to actually be stored.",
        parameters=(
            {"name": "key", "type": "Hashable", "required": True, "description": "Key to look up."},
            {
                "name": "default",
                "type": "Any",
                "required": False,
                "default": "None",
                "description": "Inserted and returned when the key is missing.",
            },
        ),
        returns="The existing value, or the newly inserted default.",
        raises=({"error": "TypeError", "when": "The key is unhashable."},),
        examples=(
            {
                "title": "Grouping",
                "code": "rows = [('EMEA', 1), ('APAC', 2), ('EMEA', 3)]\ngroups = {}\n"
                "for region, value in rows:\n    groups.setdefault(region, []).append(value)\n"
                "print(groups)",
                "output": "{'EMEA': [1, 3], 'APAC': [2]}",
            },
            {
                "title": "Why .get fails here",
                "code": "groups = {}\ngroups.get('EMEA', []).append(1)\nprint(groups)",
                "output": "{}",
            },
            {
                "title": "It does not overwrite",
                "code": "d = {'a': 1}\nprint(d.setdefault('a', 99), d)",
                "output": "1 {'a': 1}",
            },
        ),
        real_world_usage="Grouping records by a key, building an index of lists, and "
        "populating a nested configuration structure.",
        common_mistakes=(
            {
                "mistake": "d.get(key, []).append(x)",
                "fix": "The default is never stored, so the append is lost. That is exactly "
                "what setdefault fixes.",
            },
            {
                "mistake": "setdefault with an expensive default",
                "fix": "The default is evaluated on every call, even when the key exists. Use "
                "collections.defaultdict, whose factory is only called when needed.",
            },
            {
                "mistake": "Using it for plain counting",
                "fix": "collections.Counter is clearer for counts.",
            },
        ),
        performance_notes="O(1), one hash lookup — better than a separate `in` test followed "
        "by an assignment. But the default argument is constructed every call, which "
        "defaultdict avoids.",
        security_notes="",
        related=("dict.get", "dict.items", "collections.defaultdict", "collections.Counter"),
        keywords=("group by", "default value", "insert if missing", "grouping", "index"),
        lesson_slugs=("dictionaries",),
    ),
    ReferenceSpec(
        key="list.pop",
        title="list.pop()",
        kind="method",
        module="builtins",
        signature="list.pop(index=-1) -> item",
        summary="Remove and return an item — O(1) from the end, O(n) from anywhere else.",
        description="`pop()` with no argument makes a list a perfectly good stack. `pop(0)` "
        "makes it a bad queue, because every remaining element shifts left.",
        parameters=(
            {
                "name": "index",
                "type": "int",
                "required": False,
                "default": "-1",
                "description": "Position to remove; the last item by default.",
            },
        ),
        returns="The removed item.",
        raises=(
            {"error": "IndexError", "when": "The list is empty, or the index is out of range."},
        ),
        examples=(
            {
                "title": "As a stack",
                "code": "stack = [1, 2, 3]\nprint(stack.pop(), stack)",
                "output": "3 [1, 2]",
            },
            {
                "title": "From the front — correct but O(n)",
                "code": "queue = [1, 2, 3]\nprint(queue.pop(0), queue)",
                "output": "1 [2, 3]",
            },
            {
                "title": "The O(1) queue",
                "code": "from collections import deque\nq = deque([1, 2, 3])\n"
                "print(q.popleft(), list(q))",
                "output": "1 [2, 3]",
            },
            {
                "title": "Empty is an error",
                "code": "[].pop()",
                "output": "IndexError: pop from empty list",
            },
        ),
        real_world_usage="Undo stacks, depth-first traversal, and draining a work list.",
        common_mistakes=(
            {
                "mistake": "pop(0) in a loop to drain a queue",
                "fix": "That is O(n^2). Use collections.deque.popleft().",
            },
            {
                "mistake": "Popping while iterating the same list",
                "fix": "Indices shift and elements are skipped. Iterate a copy or use a "
                "while loop with explicit bounds.",
            },
            {
                "mistake": "Not handling the empty case",
                "fix": "IndexError. Test the list first, or catch it.",
            },
        ),
        performance_notes="O(1) at the end, O(n) elsewhere because of the shift. deque is "
        "O(1) at both ends.",
        security_notes="",
        related=("list", "list.append", "collections.deque"),
        keywords=("stack", "queue", "remove", "lifo", "fifo", "popleft"),
        lesson_slugs=("lists",),
    ),
    ReferenceSpec(
        key="collections.deque",
        title="collections.deque",
        kind="class",
        module="collections",
        signature="deque(iterable=(), maxlen=None)",
        summary="A double-ended queue: O(1) appends and pops at both ends, and a free "
        "fixed-size sliding window via `maxlen`.",
        description="The answer to 'a list is a bad queue'. Backed by a doubly linked list of "
        "blocks, so both ends are cheap — and the middle is not.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": False,
                "default": "()",
                "description": "Initial contents.",
            },
            {
                "name": "maxlen",
                "type": "int | None",
                "required": False,
                "default": "None",
                "description": "When set, appending past the limit discards from the other end.",
            },
        ),
        returns="A deque.",
        raises=({"error": "IndexError", "when": "Popping from an empty deque."},),
        examples=(
            {
                "title": "Both ends are O(1)",
                "code": "from collections import deque\nd = deque([2, 3])\nd.appendleft(1)\n"
                "d.append(4)\nprint(list(d), d.popleft(), d.pop())",
                "output": "[1, 2, 3, 4] 1 4",
            },
            {
                "title": "A sliding window for free",
                "code": "from collections import deque\nw = deque(maxlen=3)\n"
                "for n in [1, 2, 3, 4, 5]:\n    w.append(n)\nprint(list(w))",
                "output": "[3, 4, 5]",
            },
            {
                "title": "Rotation",
                "code": "from collections import deque\nd = deque([1, 2, 3])\nd.rotate(1)\n"
                "print(list(d))",
                "output": "[3, 1, 2]",
            },
        ),
        real_world_usage="Breadth-first search frontiers, the last N log lines kept for a "
        "crash report, rate limiters holding recent timestamps, and any producer/consumer "
        "buffer in a single thread.",
        common_mistakes=(
            {
                "mistake": "Indexing the middle in a loop",
                "fix": "d[n // 2] is O(n). If you need random access, use a list.",
            },
            {
                "mistake": "Assuming deque is fully thread-safe",
                "fix": "append and pop are atomic; a read-then-write sequence is not. Use "
                "queue.Queue across threads.",
            },
            {
                "mistake": "Forgetting maxlen silently discards",
                "fix": "That is the feature, but it means data loss if you did not intend it.",
            },
        ),
        performance_notes="append, appendleft, pop, popleft all O(1). Indexing is O(n) towards "
        "the middle. Slightly more memory per element than a list.",
        security_notes="`deque(maxlen=n)` bounds memory by construction, which makes it a good "
        "buffer for untrusted input where an unbounded list would be an exhaustion vector.",
        related=("list", "list.pop", "heapq.heappush", "queue.Queue"),
        keywords=("queue", "fifo", "sliding window", "maxlen", "popleft", "bfs", "ring buffer"),
        lesson_slugs=("stacks-queues-heaps",),
    ),
    ReferenceSpec(
        key="collections.Counter",
        title="collections.Counter",
        kind="class",
        module="collections",
        signature="Counter(iterable_or_mapping=None, **kwargs)",
        summary="A dict subclass for counting hashable things, with `most_common` and "
        "arithmetic between counters.",
        description="Counting is common enough to deserve a type. A missing key reads as 0 "
        "rather than raising, which removes the initialisation branch from every counting loop.",
        parameters=(
            {
                "name": "iterable_or_mapping",
                "type": "Iterable | Mapping",
                "required": False,
                "default": "None",
                "description": "Items to count, or initial counts.",
            },
        ),
        returns="A Counter.",
        raises=(),
        examples=(
            {
                "title": "Counting words",
                "code": "from collections import Counter\nprint(Counter('the the cat'.split()))",
                "output": "Counter({'the': 2, 'cat': 1})",
            },
            {
                "title": "most_common",
                "code": "from collections import Counter\nprint(Counter('aaabbc').most_common(2))",
                "output": "[('a', 3), ('b', 2)]",
            },
            {
                "title": "Missing keys are zero, and are not inserted",
                "code": "from collections import Counter\nc = Counter(a=1)\n"
                "print(c['zzz'], 'zzz' in c)",
                "output": "0 False",
            },
            {
                "title": "Arithmetic",
                "code": "from collections import Counter\nprint(Counter(a=3, b=1) - Counter(a=1))",
                "output": "Counter({'a': 2, 'b': 1})",
            },
        ),
        real_world_usage="Word and event frequencies, finding the noisiest alert rule, "
        "detecting duplicates, and comparing two inventories with subtraction.",
        common_mistakes=(
            {
                "mistake": "Relying on most_common to break ties",
                "fix": "Ties come out in insertion order, which is not alphabetical. Sort "
                "explicitly with a key when the tie-break matters.",
            },
            {
                "mistake": "Expecting a KeyError for a missing key",
                "fix": "It returns 0. Use `in` when you need to know whether it was ever seen.",
            },
            {
                "mistake": "Counting unhashable items",
                "fix": "Convert lists to tuples first.",
            },
        ),
        performance_notes="Counting is O(n) with dict-level constants. most_common(k) uses a "
        "heap and is O(n log k); most_common() with no argument sorts everything, O(n log n).",
        security_notes="Counting untrusted distinct values is unbounded memory. Cap the number "
        "of distinct keys you will track.",
        related=("dict", "dict.setdefault", "collections.defaultdict", "sorted"),
        keywords=("count", "frequency", "histogram", "most common", "tally", "duplicates"),
        lesson_slugs=("complexity-and-structure-choice",),
    ),
    ReferenceSpec(
        key="collections.defaultdict",
        title="collections.defaultdict",
        kind="class",
        module="collections",
        signature="defaultdict(default_factory=None, ...)",
        summary="A dict that creates a missing value by calling a factory, instead of raising.",
        description="The grouping idiom without `setdefault`'s wasted default construction. "
        "The factory is called only when a key is genuinely absent.",
        parameters=(
            {
                "name": "default_factory",
                "type": "Callable[[], Any] | None",
                "required": False,
                "default": "None",
                "description": "Zero-argument callable producing the default, e.g. list or int.",
            },
        ),
        returns="A defaultdict.",
        raises=(
            {
                "error": "KeyError",
                "when": "default_factory is None — then it behaves like a plain dict.",
            },
        ),
        examples=(
            {
                "title": "Grouping",
                "code": "from collections import defaultdict\ngroups = defaultdict(list)\n"
                "for region, value in [('EMEA', 1), ('APAC', 2), ('EMEA', 3)]:\n"
                "    groups[region].append(value)\nprint(dict(groups))",
                "output": "{'EMEA': [1, 3], 'APAC': [2]}",
            },
            {
                "title": "Counting",
                "code": "from collections import defaultdict\ncounts = defaultdict(int)\n"
                "for c in 'aab':\n    counts[c] += 1\nprint(dict(counts))",
                "output": "{'a': 2, 'b': 1}",
            },
            {
                "title": "Reading inserts, which surprises people",
                "code": "from collections import defaultdict\nd = defaultdict(list)\n"
                "d['nope']\nprint(dict(d))",
                "output": "{'nope': []}",
            },
        ),
        real_world_usage="Grouping records by key, adjacency lists in a graph, and "
        "accumulating per-category totals.",
        common_mistakes=(
            {
                "mistake": "Merely reading a missing key",
                "fix": "That inserts it. Use .get() to check without mutating, or convert to "
                "dict before returning it to a caller.",
            },
            {
                "mistake": "defaultdict(list()) instead of defaultdict(list)",
                "fix": "Pass the factory itself, not a call to it.",
            },
            {
                "mistake": "Returning a defaultdict from an API",
                "fix": "Callers get silent empty values for typos. Convert with dict() at the "
                "boundary.",
            },
        ),
        performance_notes="Faster than setdefault when defaults are expensive, because the "
        "factory is only called on a real miss.",
        security_notes="Reading attacker-supplied keys inserts them, so an untrusted lookup "
        "loop can grow memory without bound.",
        related=("dict.setdefault", "collections.Counter", "dict"),
        keywords=("group by", "autovivify", "missing key", "factory", "adjacency"),
        lesson_slugs=("dictionaries",),
    ),
    ReferenceSpec(
        key="heapq.heappush",
        title="heapq — heappush, heappop, nlargest",
        kind="function",
        module="heapq",
        signature="heappush(heap, item) | heappop(heap) -> item | nlargest(n, iterable, key=None)",
        summary="Maintain a min-heap inside a plain list: cheapest-first access in O(log n), "
        "and top-k in O(n log k).",
        description="There is no heap *type* — `heapq` maintains an invariant inside a list "
        "you own. Only index 0 is guaranteed to be the smallest; the rest is a shape, not an "
        "order, so printing a heap looks scrambled and is correct.",
        parameters=(
            {
                "name": "heap",
                "type": "list",
                "required": True,
                "description": "A list maintained in heap order. Use heapify() on an existing list.",
            },
            {
                "name": "item",
                "type": "Any",
                "required": True,
                "description": "Comparable item, often a (priority, tiebreak, payload) tuple.",
            },
        ),
        returns="heappush returns None; heappop returns the smallest item.",
        raises=(
            {"error": "IndexError", "when": "Popping from an empty heap."},
            {"error": "TypeError", "when": "Items are not mutually comparable."},
        ),
        examples=(
            {
                "title": "Smallest first",
                "code": "import heapq\nh = [5, 1, 3]\nheapq.heapify(h)\nheapq.heappush(h, 2)\n"
                "print(heapq.heappop(h), heapq.heappop(h))",
                "output": "1 2",
            },
            {
                "title": "Priorities with a payload",
                "code": "import heapq\ntasks = []\nfor i, (pri, name) in enumerate("
                "[(3, 'email'), (1, 'alert')]):\n"
                "    heapq.heappush(tasks, (pri, i, name))\nprint(heapq.heappop(tasks))",
                "output": "(1, 1, 'alert')",
            },
            {
                "title": "Top-k without a full sort",
                "code": "import heapq\nprint(heapq.nlargest(2, [5, 82, 13, 99, 41]))",
                "output": "[99, 82]",
            },
            {
                "title": "A max-heap by negating",
                "code": "import heapq\nh = []\nfor n in (5, 9, 1):\n    heapq.heappush(h, -n)\n"
                "print(-heapq.heappop(h))",
                "output": "9",
            },
        ),
        real_world_usage="Priority task queues, merging sorted files without loading them, "
        "Dijkstra's algorithm, and 'top ten of a million' leaderboards.",
        common_mistakes=(
            {
                "mistake": "Printing a heap and expecting sorted output",
                "fix": "Only h[0] is the minimum. heappop repeatedly for full order.",
            },
            {
                "mistake": "Expecting a max-heap",
                "fix": "heapq is min-only. Negate numbers, or use nlargest.",
            },
            {
                "mistake": "Pushing tuples whose payload gets compared on a tie",
                "fix": "Two equal priorities make Python compare the payload, which raises "
                "for dicts. Add a monotonic counter as the second element.",
            },
            {
                "mistake": "Sorting a list you are using as a heap",
                "fix": "Sorted order is a valid heap, but any other manual mutation breaks "
                "the invariant silently.",
            },
        ),
        performance_notes="heapify O(n); push and pop O(log n); reading the minimum O(1). "
        "nlargest/nsmallest are O(n log k) — much better than a full sort when k is small, "
        "and worse when k approaches n, where you should just sort.",
        security_notes="If untrusted input controls priorities, it controls execution order. "
        "Bound the queue size: an unbounded priority queue is a memory vector.",
        related=("sorted", "collections.deque", "bisect.insort", "tuple"),
        keywords=("priority queue", "min heap", "top k", "nlargest", "dijkstra", "scheduling"),
        lesson_slugs=("stacks-queues-heaps",),
    ),
    ReferenceSpec(
        key="bisect.insort",
        title="bisect — bisect_left, bisect_right, insort",
        kind="function",
        module="bisect",
        signature="bisect_left(a, x) -> int | bisect_right(a, x) -> int | insort(a, x) -> None",
        summary="Binary search over an already-sorted sequence, and insertion that keeps it "
        "sorted.",
        description="`bisect` **assumes** the sequence is sorted and does not check. On "
        "unsorted input it returns a confident wrong answer rather than raising, which is "
        "worse than a crash.",
        parameters=(
            {
                "name": "a",
                "type": "Sequence",
                "required": True,
                "description": "A sequence already in ascending order.",
            },
            {
                "name": "x",
                "type": "Any",
                "required": True,
                "description": "Value to locate or insert.",
            },
            {
                "name": "key",
                "type": "Callable | None",
                "required": False,
                "default": "None",
                "description": "Extracts the comparison value (Python 3.10+).",
            },
        ),
        returns="An index, or None for insort.",
        raises=(),
        examples=(
            {
                "title": "Where would it go?",
                "code": "import bisect\nscores = [10, 20, 30]\n"
                "print(bisect.bisect_left(scores, 20), bisect.bisect_right(scores, 20))",
                "output": "1 2",
            },
            {
                "title": "Insert and stay sorted",
                "code": "import bisect\nscores = [10, 20, 30]\nbisect.insort(scores, 25)\n"
                "print(scores)",
                "output": "[10, 20, 25, 30]",
            },
            {
                "title": "Grade lookup, the classic use",
                "code": "import bisect\nbounds = [60, 70, 80, 90]\ngrades = 'FDCBA'\n"
                "print(grades[bisect.bisect_right(bounds, 85)])",
                "output": "B",
            },
            {
                "title": "Wrong answer on unsorted data",
                "code": "import bisect\nprint(bisect.bisect_left([3, 1, 2], 2))",
                "output": "2",
            },
        ),
        real_world_usage="Banding a value into a range (grades, tax brackets, latency "
        "buckets), maintaining a sorted leaderboard, and finding the newest record before a "
        "timestamp.",
        common_mistakes=(
            {
                "mistake": "Using bisect on unsorted data",
                "fix": "It cannot detect this. Sort first, or maintain order as you insert.",
            },
            {
                "mistake": "Assuming insort is O(log n)",
                "fix": "The search is, the insert is not — the tail has to shift, so insort "
                "is O(n). Fine for read-heavy data, wrong for a write-heavy queue.",
            },
            {
                "mistake": "Confusing bisect_left with bisect_right",
                "fix": "They differ only for values equal to an existing element: left "
                "returns the position before them, right after.",
            },
        ),
        performance_notes="Search O(log n); insort O(n) because of the shift. If inserts "
        "dominate, use a heap, or the third-party sortedcontainers.",
        security_notes="",
        related=("sorted", "list", "heapq.heappush"),
        keywords=("binary search", "sorted insert", "buckets", "brackets", "insort", "bands"),
        lesson_slugs=("stacks-queues-heaps",),
    ),
)

STDLIB: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        key="json.load",
        title="json.load()",
        kind="function",
        module="json",
        signature="json.load(fp, **kwargs) -> Any",
        summary="Parse JSON from a file object. The `s`-less twin of `json.loads`.",
        description="`load` reads from a file, `loads` from a string. Remembering which is "
        "which is easier if you read the `s` as 'string'.",
        parameters=(
            {
                "name": "fp",
                "type": "IO[str]",
                "required": True,
                "description": "An open text file object.",
            },
            {
                "name": "object_hook",
                "type": "Callable",
                "required": False,
                "description": "Called on every decoded object, for custom types.",
            },
        ),
        returns="dict, list, str, int, float, bool or None.",
        raises=(
            {
                "error": "json.JSONDecodeError",
                "when": "The content is not valid JSON. It subclasses ValueError.",
            },
            {"error": "UnicodeDecodeError", "when": "The file is not valid text in its encoding."},
        ),
        examples=(
            {
                "title": "Read a config file",
                "code": 'import io, json\nfp = io.StringIO(\'{"host": "localhost"}\')\n'
                "print(json.load(fp))",
                "output": "{'host': 'localhost'}",
            },
            {
                "title": "Handle a corrupt file rather than crashing",
                "code": "import io, json\ntry:\n    json.load(io.StringIO('{oops'))\n"
                "except json.JSONDecodeError as exc:\n    print('bad json at line', exc.lineno)",
                "output": "bad json at line 1",
            },
            {
                "title": "JSON has no tuples",
                "code": "import json\nprint(json.loads('[1, 2]'))",
                "output": "[1, 2]",
            },
        ),
        real_world_usage="Configuration files, cached API responses, and fixtures in tests.",
        common_mistakes=(
            {
                "mistake": "json.load on a string",
                "fix": "Use json.loads for a string; load expects a file object.",
            },
            {
                "mistake": "Not handling JSONDecodeError",
                "fix": "A truncated or half-written file is normal in production. Catch it "
                "and decide what an empty or corrupt config means.",
            },
            {
                "mistake": "Assuming a round trip preserves types",
                "fix": "Tuples become lists, dict keys become strings, and datetimes are not "
                "supported at all.",
            },
            {
                "mistake": "Opening without encoding='utf-8'",
                "fix": "The platform default differs between machines. Always be explicit.",
            },
        ),
        performance_notes="The C accelerator makes this fast, but it builds the whole "
        "structure in memory. For files larger than memory, use JSON Lines and parse per "
        "line, or a streaming parser.",
        security_notes="JSON parsing is safe in a way `pickle` and `eval` are not — it cannot "
        "execute code. But deeply nested input can exhaust the recursion limit, and huge "
        "input exhausts memory: bound the size before parsing untrusted data.",
        related=("json.loads", "open", "csv.DictReader"),
        keywords=("parse json", "config", "decode", "jsondecodeerror", "file"),
        lesson_slugs=("file-handling",),
    ),
    ReferenceSpec(
        key="argparse.ArgumentParser",
        title="argparse.ArgumentParser",
        kind="class",
        module="argparse",
        signature="ArgumentParser(prog=None, description=None, ...)",
        summary="Build a command-line interface that parses, validates, converts and "
        "documents itself.",
        description="The reason to use it over reading `sys.argv` is not parsing — it is the "
        "free `--help`, the type conversion, the required-argument errors and the correct "
        "exit codes. A CLI is a user interface, and this is the one your users expect.",
        parameters=(
            {
                "name": "description",
                "type": "str",
                "required": False,
                "description": "Shown at the top of --help.",
            },
            {
                "name": "prog",
                "type": "str",
                "required": False,
                "description": "Program name; defaults to sys.argv[0].",
            },
        ),
        returns="A parser; `parse_args()` returns a Namespace of the parsed values.",
        raises=(
            {
                "error": "SystemExit",
                "when": "Arguments are invalid or --help was requested. Exit code 2 for a "
                "usage error.",
            },
        ),
        examples=(
            {
                "title": "A small CLI",
                "code": "import argparse\n"
                "p = argparse.ArgumentParser(description='Summarise a log')\n"
                "p.add_argument('path')\n"
                "p.add_argument('--limit', type=int, default=10)\n"
                "p.add_argument('--verbose', action='store_true')\n"
                "args = p.parse_args(['app.log', '--limit', '5'])\n"
                "print(args.path, args.limit, args.verbose)",
                "output": "app.log 5 False",
            },
            {
                "title": "Constrained choices",
                "code": "import argparse\np = argparse.ArgumentParser()\n"
                "p.add_argument('--level', choices=['debug', 'info'], default='info')\n"
                "print(p.parse_args(['--level', 'debug']).level)",
                "output": "debug",
            },
            {
                "title": "Testable, because parse_args takes a list",
                "code": "import argparse\np = argparse.ArgumentParser()\n"
                "p.add_argument('--n', type=int)\nprint(p.parse_args(['--n', '3']).n)",
                "output": "3",
            },
        ),
        real_world_usage="Every internal tool and batch job. The `--dry-run` flag on a script "
        "that changes data is close to mandatory.",
        common_mistakes=(
            {
                "mistake": "Reading sys.argv by hand",
                "fix": "You will reimplement --help, type conversion and error messages, worse.",
            },
            {
                "mistake": "type=bool",
                "fix": "bool('False') is True. Use action='store_true'.",
            },
            {
                "mistake": "Calling parse_args() with no argument in tests",
                "fix": "It reads the test runner's argv. Pass an explicit list.",
            },
            {
                "mistake": "Accepting a secret as a command-line flag",
                "fix": "Arguments are visible in the process list. Read secrets from the "
                "environment or a file.",
            },
        ),
        performance_notes="Startup cost is negligible next to anything the program then does.",
        security_notes="Command-line arguments are world-readable via the process table, so "
        "never pass passwords or tokens as flags. Validate paths from arguments before opening "
        "them — argparse checks types, not authorisation.",
        related=("logging.getLogger", "pathlib.Path"),
        keywords=("cli", "command line", "flags", "arguments", "argv", "dry-run", "help"),
        lesson_slugs=("automation",),
    ),
    ReferenceSpec(
        key="pytest.fixture",
        title="@pytest.fixture",
        kind="decorator",
        module="pytest",
        signature="@pytest.fixture(scope='function', params=None, autouse=False)",
        summary="Declare reusable test setup that pytest injects by parameter name, and tears "
        "down afterwards.",
        description="Fixtures replace setUp/tearDown with something composable: a test asks "
        "for what it needs by naming it as a parameter, and fixtures can depend on other "
        "fixtures.",
        parameters=(
            {
                "name": "scope",
                "type": "str",
                "required": False,
                "default": "'function'",
                "description": "function, class, module, package or session.",
            },
            {
                "name": "params",
                "type": "list",
                "required": False,
                "description": "Run every dependent test once per value.",
            },
            {
                "name": "autouse",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Apply without being requested.",
            },
        ),
        returns="A fixture function; its return value, or what it yields, is injected.",
        raises=(),
        examples=(
            {
                "title": "Setup and teardown around a yield",
                "code": "import pytest\n\n@pytest.fixture\ndef account():\n"
                "    data = {'balance': 100}\n    yield data\n    data.clear()\n\n"
                "def test_balance(account):\n    assert account['balance'] == 100\n\n"
                "print('fixture injected by name')",
                "output": "fixture injected by name",
            },
            {
                "title": "Parametrised, so one test becomes several",
                "code": "import pytest\n\n@pytest.fixture(params=[1, 2])\ndef n(request):\n"
                "    return request.param\n\ndef test_positive(n):\n    assert n > 0\n\n"
                "print('runs twice')",
                "output": "runs twice",
            },
        ),
        real_world_usage="Temporary directories via the builtin tmp_path, database sessions "
        "rolled back after each test, fake clocks, and prebuilt domain objects.",
        common_mistakes=(
            {
                "mistake": "scope='session' for mutable state",
                "fix": "Tests then leak into each other and pass or fail depending on order. "
                "Keep mutable fixtures function-scoped.",
            },
            {
                "mistake": "return instead of yield when cleanup is needed",
                "fix": "Only the yield form runs teardown.",
            },
            {
                "mistake": "autouse everywhere",
                "fix": "It hides why a test passes. Prefer explicit parameters.",
            },
            {
                "mistake": "Building elaborate fixtures for simple data",
                "fix": "A literal in the test is clearer than indirection through a fixture.",
            },
        ),
        performance_notes="Broader scopes cost less setup but risk shared state. tmp_path and "
        "monkeypatch are cheap; a session-scoped database is the usual real win.",
        security_notes="Never point a test fixture at a production database or a real "
        "credential — fixtures run automatically and destructively.",
        related=("pytest.raises", "unittest.mock.patch"),
        keywords=("test setup", "teardown", "fixture", "tmp_path", "parametrise", "injection"),
        lesson_slugs=("testing",),
    ),
    ReferenceSpec(
        key="unittest.mock.patch",
        title="unittest.mock.patch()",
        kind="function",
        module="unittest.mock",
        signature="patch(target, new=DEFAULT, autospec=None, **kwargs)",
        summary="Temporarily replace an object with a mock, restoring it afterwards — as a "
        "decorator, a context manager, or manually.",
        description="Patch **where the name is looked up**, not where it is defined. If "
        "`myapp.service` does `from requests import get`, you patch "
        "`myapp.service.get` — patching `requests.get` will not affect the already-bound name.",
        parameters=(
            {
                "name": "target",
                "type": "str",
                "required": True,
                "description": "Dotted path to the name as the code under test resolves it.",
            },
            {
                "name": "autospec",
                "type": "bool",
                "required": False,
                "description": "Build the mock from the real signature, so wrong calls fail.",
            },
            {
                "name": "return_value / side_effect",
                "type": "Any",
                "required": False,
                "description": "What the mock returns, or an exception/callable to invoke.",
            },
        ),
        returns="A MagicMock, injected or bound as the context variable.",
        raises=(
            {
                "error": "AttributeError",
                "when": "The target path does not exist — which is the usual sign of "
                "patching the wrong place.",
            },
        ),
        examples=(
            {
                "title": "As a context manager",
                "code": "from unittest.mock import patch\nimport os\n\n"
                "with patch.dict(os.environ, {'MODE': 'test'}):\n    print(os.environ['MODE'])\n"
                "print('MODE' in os.environ)",
                "output": "test\nFalse",
            },
            {
                "title": "Asserting how it was called",
                "code": "from unittest.mock import MagicMock\nsend = MagicMock(return_value=1)\n"
                "send('GET', '/things')\nsend.assert_called_once_with('GET', '/things')\n"
                "print('call recorded')",
                "output": "call recorded",
            },
            {
                "title": "Raising, to test the failure path",
                "code": "from unittest.mock import MagicMock\n"
                "flaky = MagicMock(side_effect=TimeoutError('too slow'))\ntry:\n    flaky()\n"
                "except TimeoutError as exc:\n    print(exc)",
                "output": "too slow",
            },
        ),
        real_world_usage="Simulating a network failure, freezing time, avoiding a real email "
        "send in tests, and asserting an external call was made with the right arguments.",
        common_mistakes=(
            {
                "mistake": "Patching where the object is defined",
                "fix": "Patch where it is *used*. This is the single commonest mock error.",
            },
            {
                "mistake": "Mocking without autospec",
                "fix": "A plain MagicMock accepts any call, so a signature change leaves the "
                "test passing against code that is now broken.",
            },
            {
                "mistake": "Mocking the thing you are testing",
                "fix": "Then the test asserts your mock works. Mock at the boundary only.",
            },
            {
                "mistake": "Reaching for a mock when injection would do",
                "fix": "Passing a fake collaborator in is simpler, faster and survives "
                "refactoring — see the api-client-sdk project.",
            },
        ),
        performance_notes="Mocks are fast; over-mocking is slow to *maintain*. Tests that "
        "mock deeply break on every refactor.",
        security_notes="Use patch.dict for environment variables so real secrets are never "
        "read, and never let a test fall through to a live endpoint.",
        related=("pytest.fixture", "pytest.raises"),
        keywords=("mock", "patch", "stub", "fake", "monkeypatch", "autospec", "side_effect"),
        lesson_slugs=("testing",),
    ),
    ReferenceSpec(
        key="urllib.request.urlopen",
        title="urllib.request.urlopen()",
        kind="function",
        module="urllib.request",
        signature="urlopen(url, data=None, timeout=...) -> HTTPResponse",
        summary="Make an HTTP request using only the standard library — verbose, but with "
        "nothing to install.",
        description="`requests` is nicer and is what most projects use. `urlopen` matters when "
        "you cannot add a dependency: a bootstrap script, a container with no wheels, or a "
        "sandbox.",
        parameters=(
            {
                "name": "url",
                "type": "str | Request",
                "required": True,
                "description": "URL, or a Request for custom headers and methods.",
            },
            {
                "name": "data",
                "type": "bytes | None",
                "required": False,
                "default": "None",
                "description": "Body. Its presence makes the request a POST.",
            },
            {
                "name": "timeout",
                "type": "float",
                "required": False,
                "description": "Seconds. Always pass it — there is no default worth relying on.",
            },
        ),
        returns="An HTTPResponse context manager; `.read()` gives bytes.",
        raises=(
            {"error": "urllib.error.HTTPError", "when": "The server returned 4xx or 5xx."},
            {"error": "urllib.error.URLError", "when": "DNS failure, refused connection, timeout."},
        ),
        examples=(
            {
                "title": "The shape of a GET",
                "code": "from urllib.request import Request\n"
                "req = Request('https://example.com/api', headers={'Accept': 'application/json'})\n"
                "print(req.get_method(), req.get_header('Accept'))",
                "output": "GET application/json",
            },
            {
                "title": "A POST is implied by data",
                "code": "from urllib.request import Request\n"
                "req = Request('https://example.com/api', data=b'{}')\nprint(req.get_method())",
                "output": "POST",
            },
            {
                "title": "Decoding is your job",
                "code": "raw = b'{\"ok\": true}'\nimport json\n"
                "print(json.loads(raw.decode('utf-8')))",
                "output": "{'ok': True}",
            },
        ),
        real_world_usage="Install and bootstrap scripts, health checks in a minimal image, "
        "and anywhere adding a dependency is not an option.",
        common_mistakes=(
            {
                "mistake": "Omitting timeout",
                "fix": "A hung connection hangs your program indefinitely. Always pass one.",
            },
            {
                "mistake": "Expecting a non-2xx to return normally",
                "fix": "It raises HTTPError, unlike requests which returns a response you "
                "must check.",
            },
            {
                "mistake": "Forgetting .read() returns bytes",
                "fix": "Decode before parsing as text or JSON.",
            },
            {
                "mistake": "Not closing the response",
                "fix": "Use it as a context manager.",
            },
        ),
        performance_notes="No connection pooling, so repeated calls to one host are slower "
        "than a `requests.Session`. Fine for a handful of requests.",
        security_notes="Certificates are verified by default — do not disable that. Never "
        "build a URL from unvalidated user input, which invites server-side request forgery "
        "against internal addresses.",
        related=("requests.get", "json.loads"),
        keywords=("http", "stdlib request", "get", "post", "timeout", "no dependencies"),
        lesson_slugs=("apis-and-http",),
    ),
)

ADDITIONAL_REFERENCE: tuple[ReferenceSpec, ...] = (
    BUILTIN_TYPES + BUILTIN_FUNCTIONS + ERRORS + CONTAINERS + STDLIB
)
