"""Module 01–02: programming fundamentals and control flow.

Four lessons taking a learner from "what is a program?" to writing loops that
terminate. Every exercise here is graded by running real code in the sandbox.
"""

from __future__ import annotations

from app.content.schema import Example, ExerciseSpec, HintSpec, LessonSpec, ModuleSpec
from app.models.enums import ExerciseKind, GraderKind, SkillLevel

# ---------------------------------------------------------------------------
# Lesson 1 — What Python is and how it runs
# ---------------------------------------------------------------------------

PYTHON_FUNDAMENTALS = LessonSpec(
    slug="python-fundamentals",
    title="What Python Is, and What Happens When You Run It",
    summary="Programs, interpreters, bytecode and the REPL — the mental model everything "
    "else rests on.",
    level=SkillLevel.BEGINNER,
    estimated_minutes=18,
    concepts=("variables",),
    reference_keys=("print", "input"),
    body="""\
## A program is a plan someone else executes

Writing code is writing instructions precisely enough that a machine can follow
them without asking you what you meant. That is the whole job. Most beginner
frustration is not "I can't code" — it is "I said something ambiguous and the
machine did exactly what I said."

Python's appeal is that the distance between what you mean and what you type is
short:

```python
print("Hello, world")
```

That is a complete, runnable program.

## What actually happens when you run it

People often say Python is "interpreted", which is true but too vague to be
useful. Here is the real sequence:

```
your source (.py)
      │  1. parse   → is this valid Python?
      ▼
  syntax tree
      │  2. compile → bytecode (.pyc, cached in __pycache__)
      ▼
   bytecode
      │  3. execute → the CPython virtual machine runs it, instruction by instruction
      ▼
    output
```

Three consequences follow directly, and they explain most of what confuses
beginners:

1. **Syntax errors happen before anything runs.** If line 40 has a typo, line 1
   never executes. There is no partial run.
2. **Everything else happens *during* execution.** Python does not check that a
   variable exists, or that a type is right, until the line actually runs. A
   bug on a rarely-taken branch can sit undiscovered for months.
3. **`__pycache__` is a cache, not your program.** Safe to delete; Python
   regenerates it.

## The interpreter is a conversation

Run `python` with no arguments and you get a REPL — Read, Evaluate, Print, Loop:

```
>>> 2 + 2
4
>>> name = "Ada"
>>> name.upper()
'ADA'
```

This is the single most under-used tool by beginners. When you are unsure what
something does, do not reason about it — ask. In this platform, the Code Lab is
your REPL.

## Comments and readability

```python
# A comment explains WHY, not WHAT.
total = price * 1.2   # 20% VAT — required by UK invoicing rules
```

`total = price * 1.2` already says what happens. What the reader cannot recover
from the code is *why* 1.2. That is what the comment is for.
""",
    sections={
        "what_is_it": "Python is a general-purpose programming language, and CPython is the "
        "program that reads your source, compiles it to bytecode, and executes that bytecode "
        "on a virtual machine.",
        "why_it_exists": "Guido van Rossum designed Python to optimise for readability and "
        "programmer time rather than machine time. Code is read far more often than it is "
        "written; Python's syntax is a bet on that asymmetry.",
        "how_it_works": "Source is parsed into a syntax tree, compiled to bytecode (cached "
        "in __pycache__), then executed instruction by instruction. Syntax errors surface at "
        "compile time; name and type errors surface at run time, on the line that runs.",
        "when_to_use": "Automation, data work, web backends, testing, scripting, glue "
        "between systems, and anywhere developer speed matters more than raw execution speed.",
        "when_not_to_use": "Hard real-time systems, tight numeric inner loops where you "
        "cannot delegate to a C library, memory-constrained embedded targets, and anything "
        "needing sub-millisecond deterministic latency.",
        "common_mistakes": "Expecting a syntax error to be reported at the exact character "
        "that is wrong (it is usually reported *after* it); assuming code that never runs is "
        "correct because there was no error; editing a file and running a different one.",
        "real_world": "In a typical engineering team Python runs the CI scripts, the data "
        "pipelines, the internal APIs and the test automation. It is often the language that "
        "holds the other languages together.",
        "alternatives": "Go for high-concurrency network services with static typing; Rust "
        "for performance and memory safety; TypeScript when the code must also run in a "
        "browser; SQL when the work is really a query.",
        "performance": "CPython trades speed for flexibility. Interpretation costs roughly "
        "10–100× a compiled language on pure Python loops — which is irrelevant for I/O-bound "
        "work, and fatal for numeric inner loops. The standard answer is to push hot loops "
        "into C libraries (NumPy, Polars) rather than to rewrite everything.",
        "security": "Running code means trusting it. Never `pip install` a package you have "
        "not checked, never run a script from an untrusted source on a machine you care "
        "about, and never pass user input to `eval()` or `exec()`.",
    },
    starter_code='print("Hello, world")\n',
    examples=(
        Example(
            title="Your first program",
            code='print("Hello, world")',
            output="Hello, world",
            explanation="`print` is a built-in function. The parentheses call it; the text "
            "in quotes is the argument you pass.",
        ),
        Example(
            title="Two statements run in order",
            code='print("First")\nprint("Second")',
            output="First\nSecond",
            explanation="Python executes top to bottom. Order is not a suggestion — it is "
            "the semantics.",
        ),
        Example(
            title="A syntax error stops everything",
            code='print("this never runs")\nprint("missing paren"',
            output='  File "main.py", line 2\n    print("missing paren"\n         ^\n'
            "SyntaxError: '(' was never closed",
            explanation="Note that the *first* line did not print. Compilation failed, so "
            "nothing executed. Syntax errors are all-or-nothing.",
        ),
    ),
    visualizations=(
        {
            "kind": "pipeline",
            "title": "From source to output",
            "steps": ["source .py", "syntax tree", "bytecode", "CPython VM", "output"],
        },
    ),
    exercises=(
        ExerciseSpec(
            slug="fundamentals-hello",
            title="Print a greeting",
            prompt="Make the program print exactly:\n\n```\nHello, PyForge\n```\n\n"
            "Case and spelling matter — output comparison is exact.",
            kind=ExerciseKind.CODE,
            level=SkillLevel.BEGINNER,
            difficulty=0.1,
            estimated_minutes=3,
            xp_reward=15,
            starter_files={"main.py": "# Print the greeting below\n"},
            grader=GraderKind.STDOUT_MATCH,
            grader_config={"expected_stdout": "Hello, PyForge", "entrypoint": "main.py"},
            concepts=("variables",),
            hints=(
                HintSpec("The built-in function that writes to the screen is `print`."),
                HintSpec('Text values go inside quotes: `"like this"`.'),
                HintSpec(
                    "Call a function by writing its name followed by parentheses "
                    "containing the argument."
                ),
                HintSpec('The shape is: `print("...")` — with the exact greeting inside.'),
            ),
            solution_files={"main.py": 'print("Hello, PyForge")\n'},
            solution_explanation="`print` writes its argument to standard output, then adds "
            "a newline. The string literal is the argument.",
        ),
        ExerciseSpec(
            slug="fundamentals-syntax-fix",
            title="Debug: fix the syntax errors",
            prompt="This program has three syntax errors. Fix them so it prints:\n\n"
            "```\nPython runs top to bottom\nOne error stops everything\n```\n\n"
            "Read the error message, fix the *first* problem only, and run again. "
            "Chasing all three at once is how you introduce a fourth.",
            kind=ExerciseKind.DEBUG,
            level=SkillLevel.BEGINNER,
            difficulty=0.25,
            estimated_minutes=6,
            xp_reward=30,
            starter_files={
                "main.py": 'print("Python runs top to bottom"\n'
                "print('One error stops everything\")\n"
                'prnt("")\n'
            },
            grader=GraderKind.STDOUT_MATCH,
            grader_config={
                "expected_stdout": "Python runs top to bottom\nOne error stops everything",
                "entrypoint": "main.py",
            },
            concepts=("variables",),
            hints=(
                HintSpec(
                    "Run it. The first error names a line number — start there and nowhere else."
                ),
                HintSpec(
                    "Every opening parenthesis needs a matching closing one, and quotes "
                    'must match in kind: open with `"`, close with `"`.'
                ),
                HintSpec(
                    "Line 3 is not a syntax error at all — it is a *name* error. Look "
                    "carefully at the spelling of the function, and ask whether that "
                    "line should exist."
                ),
                HintSpec(
                    "Line 1 is missing `)`. Line 2 opens with `'` and closes with `\"`. "
                    "Line 3 misspells `print` and prints an empty line the expected "
                    "output does not contain."
                ),
            ),
            solution_files={
                "main.py": 'print("Python runs top to bottom")\n'
                'print("One error stops everything")\n'
            },
            solution_explanation="Two syntax errors (unclosed call, mismatched quotes) and "
            "one line that should be deleted. The lesson: fix one error, re-run, repeat. "
            "Errors after the first are often phantoms caused by the first.",
            misconception_rules=(
                {"pattern": "NameError", "misconception": "undefined-name"},
                {"pattern": "SyntaxError", "misconception": "syntax-error"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 2 — Variables and data types
# ---------------------------------------------------------------------------

VARIABLES_AND_TYPES = LessonSpec(
    slug="variables-and-data-types",
    title="Variables, Types and the Label Model",
    summary="Names are labels attached to objects, not boxes holding values — and that one "
    "idea explains a whole category of bugs.",
    level=SkillLevel.BEGINNER,
    estimated_minutes=25,
    concepts=("variables", "data-types", "operators", "io-basics"),
    reference_keys=("int", "str", "float", "input", "print"),
    body="""\
## Names are labels, not boxes

Most languages teach variables as boxes: a named container you put a value into.
Python does not work that way, and pretending it does will eventually cost you
an afternoon.

In Python, **an assignment binds a name to an object**:

```python
x = 10
y = x
```

```
x ─────┐
       ▼
     [ 10 ]        one integer object, two labels
       ▲
y ─────┘
```

Now:

```python
x = 20      # rebinds x to a NEW object; y still points at 10
print(y)    # 10
```

Rebinding a name never touches the object. This looks like the box model, so
beginners never notice — until a mutable object appears:

```python
a = [1, 2, 3]
b = a          # second label for the SAME list
b.append(4)
print(a)       # [1, 2, 3, 4]  ← surprising, if you believed in boxes
```

Nothing copied. `b.append(4)` mutated the one list both names refer to. When you
want an independent list, ask for one: `b = a.copy()`.

## The core types

| Type | Example | Mutable? | Use it for |
| --- | --- | --- | --- |
| `int` | `42`, `-7` | no | whole numbers, counts, ids |
| `float` | `3.14`, `2.0` | no | measurements, averages |
| `bool` | `True`, `False` | no | yes/no decisions |
| `str` | `"hello"` | no | text |
| `None` | `None` | n/a | "no value yet" / "nothing to return" |

`type(value)` tells you which you have. `isinstance(value, int)` asks whether it
is one, and is the right check because it respects subclassing.

## Floats are approximations

```python
>>> 0.1 + 0.2
0.30000000000000004
```

This is not a Python bug. Binary floating point cannot represent 0.1 exactly,
any more than decimal can represent 1/3 exactly. Two rules follow:

* Never compare floats with `==`. Compare with a tolerance, or use
  `math.isclose(a, b)`.
* **Never use float for money.** Use `decimal.Decimal("19.99")`, or store
  integer pence. Financial systems that ignore this leak fractions of a currency
  unit until someone notices.

## Conversion is explicit

Python will not quietly turn a `str` into an `int` for you:

```python
age = input("Age: ")   # ALWAYS a str, even if they typed 30
age + 1                # TypeError: can only concatenate str to str
int(age) + 1           # 31
```

`input()` returning a string is the single most common beginner surprise. Get in
the habit: read, convert, then use.

## Naming

```python
n = 86400                     # what is this?
seconds_per_day = 86400       # oh.
```

`snake_case` for variables and functions, `UPPER_SNAKE_CASE` for constants,
`CapWords` for classes. Names are documentation you cannot forget to update.
""",
    sections={
        "what_is_it": "A variable is a name bound to an object. A type describes what an "
        "object is and what you can do with it.",
        "why_it_exists": "Names let you refer to a result you computed earlier and give it "
        "meaning. Types let Python (and readers) know which operations make sense.",
        "how_it_works": "Assignment creates or rebinds a name in the current namespace, "
        "pointing it at an object. Objects carry their type; names do not. Several names may "
        "refer to one object, which is what makes mutation visible through more than one name.",
        "when_to_use": "Whenever a value is used more than once, or whenever naming it makes "
        "the code explain itself.",
        "when_not_to_use": "Do not create a name for a value used exactly once in the very "
        "next line unless the name adds meaning. And never reuse one name for two unrelated "
        "purposes in the same function.",
        "common_mistakes": "Assuming `input()` returns a number; comparing floats with `==`; "
        "using float for money; believing `b = a` copies a list; shadowing a built-in by "
        "naming a variable `list`, `str`, `id` or `type`.",
        "real_world": "Configuration values, accumulator variables in loops, and function "
        "parameters are all just names bound to objects. The aliasing rule is why passing a "
        "list to a function can change the caller's list.",
        "alternatives": "For grouped values, a `dataclass` or a `NamedTuple` beats five "
        "loose variables. For constants that belong together, use an `Enum`.",
        "performance": "Small integers (-5 to 256) and short strings are interned by CPython "
        "and reused, which is why `a is b` sometimes returns True for equal values. Do not "
        "rely on it. Rebinding is cheap; copying large structures is not.",
        "security": "Never build a value that will be interpreted as code or as a query by "
        "concatenating user input. Never log a variable that holds a password or token — "
        "assume anything logged is retained.",
    },
    starter_code="""\
name = "Ada"
age = 36
height_m = 1.68

print(f"{name} is {age} years old and {height_m}m tall")
print(type(name), type(age), type(height_m))
""",
    examples=(
        Example(
            title="Rebinding vs mutating",
            code="""\
x = 10
y = x
x = 20
print("ints:", x, y)

a = [1, 2]
b = a
a.append(3)
print("lists:", a, b)
""",
            output="ints: 20 10\nlists: [1, 2, 3] [1, 2, 3]",
            explanation="Rebinding `x` left `y` alone. Mutating the list was visible through "
            "both names, because there was only ever one list.",
        ),
        Example(
            title="Conversion, and why input() bites",
            code="""\
raw = "30"
print(raw + "1")        # string concatenation
print(int(raw) + 1)     # arithmetic
print(float("2.5") * 2)
""",
            output="301\n31\n5.0",
            explanation="`+` means concatenate for strings and add for numbers. The type "
            "decides the meaning of the operator.",
        ),
        Example(
            title="Floats are not exact",
            code="""\
import math
print(0.1 + 0.2)
print(0.1 + 0.2 == 0.3)
print(math.isclose(0.1 + 0.2, 0.3))
""",
            output="0.30000000000000004\nFalse\nTrue",
            explanation="Compare floats with a tolerance. For money, use Decimal or integer "
            "minor units.",
        ),
    ),
    visualizations=(
        {
            "kind": "references",
            "title": "Two names, one list",
            "bindings": [{"name": "a", "target": "list#1"}, {"name": "b", "target": "list#1"}],
            "objects": [{"id": "list#1", "repr": "[1, 2, 3]"}],
        },
    ),
    exercises=(
        ExerciseSpec(
            slug="variables-receipt",
            title="Build a receipt line",
            prompt="""\
Complete `receipt_line(item, quantity, unit_price)` so it returns a string of
the form:

```
3 x Widget @ 2.50 = 7.50
```

Rules:
* prices are formatted to exactly two decimal places
* the total is quantity × unit price
* return the string, do not print it
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.BEGINNER,
            difficulty=0.3,
            estimated_minutes=10,
            starter_files={
                "main.py": '''\
def receipt_line(item: str, quantity: int, unit_price: float) -> str:
    """Return a formatted receipt line."""
    # Your code here
    ...
'''
            },
            hidden_files={
                "test_receipt.py": """\
from main import receipt_line


def test_basic_line():
    assert receipt_line("Widget", 3, 2.5) == "3 x Widget @ 2.50 = 7.50"


def test_single_item():
    assert receipt_line("Cable", 1, 12.0) == "1 x Cable @ 12.00 = 12.00"


def test_rounds_to_two_places():
    assert receipt_line("Nut", 7, 0.333) == "7 x Nut @ 0.33 = 2.33"


def test_returns_rather_than_prints(capsys):
    result = receipt_line("Bolt", 2, 1.0)
    assert result is not None, "the function must return the line, not print it"
    assert capsys.readouterr().out == "", "do not print inside the function"
"""
            },
            concepts=("variables", "data-types", "strings"),
            hints=(
                HintSpec('An f-string lets you drop values into text: `f"{quantity} x ..."`.'),
                HintSpec(
                    "Format specifiers go after a colon inside the braces. Two decimal "
                    "places is `:.2f`."
                ),
                HintSpec(
                    "You need three values in the string: quantity, item, unit price — "
                    "and the total, which you compute as `quantity * unit_price`."
                ),
                HintSpec(
                    "The shape is:\n```python\ntotal = quantity * unit_price\n"
                    'return f"{quantity} x {item} @ {unit_price:.2f} = {total:.2f}"\n```'
                ),
            ),
            solution_files={
                "main.py": '''\
def receipt_line(item: str, quantity: int, unit_price: float) -> str:
    """Return a formatted receipt line."""
    total = quantity * unit_price
    return f"{quantity} x {item} @ {unit_price:.2f} = {total:.2f}"
'''
            },
            solution_explanation="`:.2f` rounds for display without changing the value. Note "
            "that the function *returns* — a function that prints cannot be composed, tested "
            "or reused.",
            misconception_rules=(
                {"pattern": "do not print inside", "misconception": "missing-return"},
                {"pattern": "TypeError", "misconception": "type-mismatch"},
            ),
        ),
        ExerciseSpec(
            slug="variables-aliasing-quiz",
            title="Concept check: aliasing",
            prompt="What does this program print?\n\n```python\na = [1, 2, 3]\nb = a\n"
            "b.append(4)\nprint(len(a))\n```",
            kind=ExerciseKind.QUIZ,
            level=SkillLevel.BEGINNER,
            difficulty=0.35,
            estimated_minutes=2,
            xp_reward=15,
            grader=GraderKind.MULTIPLE_CHOICE,
            grader_config={
                "options": ["3", "4", "It raises an error", "None"],
                "correct_index": 1,
                "explanation": "`b = a` binds a second name to the same list object. "
                "`b.append(4)` mutates that one list, so `a` sees the change too and its "
                "length is 4. To get an independent list, write `b = a.copy()`.",
                "misconception_per_option": {"0": "aliasing", "2": "aliasing", "3": "aliasing"},
            },
            concepts=("variables", "lists", "mutability"),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 3 — Conditions
# ---------------------------------------------------------------------------

CONDITIONS = LessonSpec(
    slug="conditions",
    title="Making Decisions: if, elif, else",
    summary="Branching, truthiness, and writing conditions that a reader can verify at a glance.",
    level=SkillLevel.BEGINNER,
    estimated_minutes=20,
    concepts=("conditionals", "operators"),
    reference_keys=("bool", "any", "all"),
    body="""\
## The shape

```python
if temperature > 30:
    print("Hot")
elif temperature > 20:
    print("Warm")
else:
    print("Cold")
```

Exactly one branch runs. `elif` is checked only if every condition above it was
false — which means **order encodes priority**. Swap the two conditions above
and every temperature over 30 reports "Warm", with no error to tell you.

Indentation is not decoration. It is how Python knows where the block ends.
Four spaces, consistently, never tabs.

## Truthiness

Every object can be used as a condition. The falsy values are few enough to
memorise:

```
False   None   0   0.0   ""   []   {}   set()   ()
```

Everything else is truthy. So instead of:

```python
if len(items) > 0:
```

write:

```python
if items:
```

That reads as "if there are items", which is what you meant.

One trap: this idiom cannot distinguish "empty" from "missing". If `0` and
`None` mean different things in your domain, test explicitly:

```python
if count is not None:      # not `if count:` — 0 is a legitimate count
```

## Comparison chains

Python lets you write what mathematicians write:

```python
if 0 <= score <= 100:
```

That is one expression, evaluated once, with no repetition of `score`. Other
languages make you write `score >= 0 && score <= 100`.

## The `or` trap

```python
if day == "Saturday" or "Sunday":     # BUG — always true
```

`or` combines two *conditions*. `"Sunday"` on its own is a non-empty string,
which is truthy, so the whole expression is always true. Write:

```python
if day in ("Saturday", "Sunday"):
```

## Short-circuiting is a feature

`and` stops at the first falsy operand; `or` stops at the first truthy one. That
lets you guard safely in one line:

```python
if user is not None and user.is_active:   # never touches .is_active when None
```

Reverse the order and you get an AttributeError.

## Conditional expressions

```python
label = "adult" if age >= 18 else "minor"
```

Good for choosing between two values. Bad for anything longer — if you find
yourself nesting them, use an `if` statement.
""",
    sections={
        "what_is_it": "Conditional statements choose which block of code runs, based on "
        "whether an expression is true.",
        "why_it_exists": "Without branching, a program does the same thing regardless of its "
        "input. Conditions are what make a program respond to the world.",
        "how_it_works": "Python evaluates each condition in order and runs the block under "
        "the first true one, then skips the rest of the chain. Any object can be a condition; "
        "Python applies its truthiness rules.",
        "when_to_use": "Whenever behaviour depends on data: validating input, handling edge "
        "cases, choosing a code path.",
        "when_not_to_use": "When a long if/elif chain maps a value to a result, use a "
        "dictionary lookup instead — it is faster, shorter and easier to extend. When you are "
        "checking types to pick behaviour, consider polymorphism.",
        "common_mistakes": "`if x == 1 or 2:` (always true); using `=` instead of `==` "
        "(SyntaxError in a condition, which is a mercy); ordering elif branches so a broader "
        "condition shadows a narrower one; `if x:` when 0 is a valid value.",
        "real_world": "Input validation, feature flags, permission checks, retry decisions "
        "and error handling are all conditionals. In production code the risky ones are the "
        "branches you cannot easily test.",
        "alternatives": "Dictionary dispatch for value→result mapping; `match`/`case` "
        "(Python 3.10+) for structural matching; polymorphism for type-based behaviour; "
        "guard clauses with early returns to avoid nesting.",
        "performance": "Order conditions cheapest-and-most-likely first: short-circuiting "
        "means later operands may never be evaluated. A dict lookup is O(1) versus O(n) for a "
        "long elif chain, though at typical chain lengths this rarely matters.",
        "security": "Fail closed: default to denying access and grant it explicitly. An "
        "`else` that grants permission is a bug waiting for an unanticipated input. Validate "
        "before you branch, not inside each branch.",
    },
    starter_code="""\
score = 87

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "F"

print(f"Score {score} -> grade {grade}")
""",
    examples=(
        Example(
            title="Order matters",
            code="""\
def classify_wrong(n):
    if n > 0:
        return "positive"
    elif n > 100:      # unreachable: anything > 100 is already > 0
        return "large"
    return "non-positive"

print(classify_wrong(500))
""",
            output="positive",
            explanation="The `n > 100` branch can never run. Python gives no warning — a "
            "reachability bug is silent. Put the narrower condition first.",
        ),
        Example(
            title="Truthiness",
            code="""\
for value in [0, 1, "", "x", [], [0], None, {}]:
    print(repr(value), "->", bool(value))
""",
            output="0 -> False\n1 -> True\n'' -> False\n'x' -> True\n[] -> False\n"
            "[0] -> True\nNone -> False\n{} -> False",
            explanation="Note `[0]` is truthy: a list containing a falsy value is still a "
            "non-empty list.",
        ),
        Example(
            title="Short-circuit guarding",
            code="""\
user = None
if user is not None and user["name"]:
    print("has name")
else:
    print("no user")
""",
            output="no user",
            explanation="`and` never evaluates the right side, so subscripting None never "
            "happens. Swap the operands and you get a TypeError.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="conditions-shipping",
            title="Shipping cost rules",
            prompt="""\
Implement `shipping_cost(weight_kg, is_express)` against these business rules,
in this priority order:

1. Weight of 0 or less → raise `ValueError`
2. Express delivery → £14.99 regardless of weight
3. Weight over 20 kg → £24.99
4. Weight over 5 kg → £9.99
5. Otherwise → £3.99

Return a `float`.
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.BEGINNER,
            difficulty=0.4,
            estimated_minutes=12,
            starter_files={
                "main.py": '''\
def shipping_cost(weight_kg: float, is_express: bool) -> float:
    """Return the shipping cost in pounds."""
    ...
'''
            },
            hidden_files={
                "test_shipping.py": """\
import pytest

from main import shipping_cost


def test_standard_light():
    assert shipping_cost(1.0, False) == 3.99


def test_standard_medium():
    assert shipping_cost(10.0, False) == 9.99


def test_standard_heavy():
    assert shipping_cost(25.0, False) == 24.99


def test_express_beats_weight():
    assert shipping_cost(25.0, True) == 14.99
    assert shipping_cost(0.5, True) == 14.99


def test_boundaries_are_exclusive():
    assert shipping_cost(5.0, False) == 3.99
    assert shipping_cost(20.0, False) == 9.99


def test_invalid_weight_raises():
    with pytest.raises(ValueError):
        shipping_cost(0, False)
    with pytest.raises(ValueError):
        shipping_cost(-2, True)
"""
            },
            concepts=("conditionals", "operators", "exceptions"),
            hints=(
                HintSpec(
                    "The rules are given in priority order for a reason. Your `if` chain "
                    "should check them in the same order."
                ),
                HintSpec(
                    "Validation comes first. Reject the bad input before doing any work "
                    "— this is called a guard clause."
                ),
                HintSpec(
                    "'Over 5 kg' means strictly greater than 5, so exactly 5.0 falls "
                    "through to the base rate. Check your comparison operators against "
                    "the boundary tests."
                ),
                HintSpec(
                    "Structure:\n```python\nif weight_kg <= 0:\n    raise ValueError(...)\n"
                    "if is_express:\n    return 14.99\nif weight_kg > 20:\n    ...\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
def shipping_cost(weight_kg: float, is_express: bool) -> float:
    """Return the shipping cost in pounds.

    Rules are evaluated in business-priority order; express overrides weight.
    """
    if weight_kg <= 0:
        raise ValueError(f"weight must be positive, got {weight_kg}")
    if is_express:
        return 14.99
    if weight_kg > 20:
        return 24.99
    if weight_kg > 5:
        return 9.99
    return 3.99
'''
            },
            solution_explanation="Guard clause first, then rules in priority order with early "
            "returns. No `else` is needed: each `return` ends the function. This shape stays "
            "flat as rules are added, where nested if/else grows a pyramid.",
            misconception_rules=(
                {"pattern": "test_boundaries_are_exclusive", "misconception": "off-by-one"},
                {"pattern": "DID NOT RAISE", "misconception": "missing-validation"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 4 — Loops
# ---------------------------------------------------------------------------

LOOPS = LessonSpec(
    slug="loops",
    title="Repetition: for, while, and Loops That Terminate",
    summary="Iterating over data, counting with range(), and the discipline that stops a "
    "while loop running for ever.",
    level=SkillLevel.BEGINNER,
    estimated_minutes=25,
    concepts=("loops", "conditionals"),
    reference_keys=("range", "enumerate", "zip", "sum"),
    body="""\
## `for` iterates over things, not numbers

The single biggest style upgrade for a new Python programmer:

```python
# What you write in C, Java, JavaScript
for i in range(len(names)):
    print(names[i])

# What you write in Python
for name in names:
    print(name)
```

`for` walks any *iterable*: lists, strings, dicts, files, generators, database
cursors. You almost never need the index. When you genuinely do:

```python
for index, name in enumerate(names, start=1):
    print(f"{index}. {name}")
```

And when you need two sequences side by side:

```python
for name, score in zip(names, scores):
    print(name, score)
```

`zip` stops at the shorter one — silently. Pass `strict=True` (Python 3.10+) to
make a length mismatch an error instead of a quiet truncation.

## `range` counts, and it stops one short

```python
range(5)          # 0 1 2 3 4       — five values, not six
range(2, 6)       # 2 3 4 5
range(0, 10, 2)   # 0 2 4 6 8
range(5, 0, -1)   # 5 4 3 2 1
```

The end is exclusive. This is why `len(seq)` is never a valid index, and why
`range(len(seq))` produces exactly the valid indexes.

## `while` repeats until a condition changes

```python
attempts = 0
while attempts < 3:
    attempts += 1        # ← without this line, the loop never ends
    print(f"Attempt {attempts}")
```

Every `while` loop is a promise that something inside the body will eventually
make the condition false. Before you run one, answer out loud: *what changes,
and what makes it stop?* If you cannot answer, you have written an infinite
loop.

Use `for` when you know the collection. Use `while` when you are waiting for a
condition — user input, a retry budget, a queue draining.

## `break`, `continue`, and the `else` nobody expects

```python
for item in inventory:
    if item.sku == wanted:
        print("found")
        break
else:
    print("not found")     # runs only if the loop was NOT broken out of
```

`for ... else` runs the `else` when the loop completed without `break`. It reads
oddly at first, and it removes the `found = False` flag variable that otherwise
clutters every search loop.

## Never mutate what you are iterating

```python
for item in items:
    if item.expired:
        items.remove(item)   # BUG: skips elements
```

Removing shifts everything left while the loop's internal index moves right, so
alternate elements are skipped, with no error. Build a new list instead:

```python
items = [item for item in items if not item.expired]
```
""",
    sections={
        "what_is_it": "Loops execute a block repeatedly: `for` over the items of an iterable, "
        "`while` until a condition becomes false.",
        "why_it_exists": "Repetition is what makes programs scale beyond what you could type "
        "by hand. The same eight lines process eight rows or eight million.",
        "how_it_works": "`for` calls `iter()` on the iterable to get an iterator, then calls "
        "`next()` until StopIteration. `while` re-evaluates its condition before every pass. "
        "`break` exits immediately; `continue` skips to the next iteration; the loop `else` "
        "runs only when no `break` occurred.",
        "when_to_use": "for: processing every item in a collection. while: retry loops, "
        "waiting on external state, consuming until a sentinel.",
        "when_not_to_use": "When you are building a new collection from an old one, a "
        "comprehension says it in one line. When you are summing or counting, `sum()`, "
        "`max()` and `collections.Counter` are clearer and faster. When you are looping to "
        "find one item, `next(...)` with a generator expression is more direct.",
        "common_mistakes": "Forgetting to change the loop variable in a `while` (infinite "
        "loop); off-by-one from misreading `range`'s exclusive end; mutating a list while "
        "iterating it; using `range(len(x))` out of habit; shadowing the loop variable inside "
        "the body.",
        "real_world": "Every batch job, every ETL row-by-row transform, every retry policy "
        "and every paginated API client is a loop. Production loops need a bound — a maximum "
        "attempt count or a timeout — because 'until it works' is not a terminating condition.",
        "alternatives": "Comprehensions for building collections; `itertools` for chaining, "
        "grouping and windowing; `map`/`filter` for simple transforms; vectorised operations "
        "(NumPy, Pandas) when the data is numeric and large.",
        "performance": "A Python-level loop costs roughly 50–100 ns per iteration in "
        "interpreter overhead alone. Prefer built-ins written in C (`sum`, `any`, `''.join`) "
        "for hot paths. Building a string with `+=` inside a loop is quadratic — collect the "
        "parts in a list and `join` once.",
        "security": "Any loop driven by external input needs a bound. An unbounded retry "
        "loop against a failing service is a self-inflicted denial of service; an unbounded "
        "read loop on a network socket is a memory exhaustion vector.",
    },
    starter_code="""\
scores = [88, 92, 79, 95, 61]

total = 0
for score in scores:
    total += score

print(f"Count:   {len(scores)}")
print(f"Total:   {total}")
print(f"Average: {total / len(scores):.1f}")
print(f"Best:    {max(scores)}")
""",
    examples=(
        Example(
            title="enumerate beats manual counters",
            code="""\
tasks = ["write", "test", "ship"]
for position, task in enumerate(tasks, start=1):
    print(f"{position}. {task}")
""",
            output="1. write\n2. test\n3. ship",
            explanation="`start=1` gives human numbering without arithmetic in the body.",
        ),
        Example(
            title="A while loop with a bound",
            code="""\
budget = 3
attempt = 0
connected = False

while not connected and attempt < budget:
    attempt += 1
    print(f"Connecting... attempt {attempt}")
    connected = attempt == 3

print("Connected" if connected else "Gave up")
""",
            output="Connecting... attempt 1\nConnecting... attempt 2\n"
            "Connecting... attempt 3\nConnected",
            explanation="Two exit conditions: success, or the retry budget. Never write a "
            "retry loop with only the first one.",
        ),
        Example(
            title="for/else for search",
            code="""\
skus = ["A1", "B2", "C3"]
for sku in skus:
    if sku == "Z9":
        print("found")
        break
else:
    print("Z9 is not in stock")
""",
            output="Z9 is not in stock",
            explanation="No flag variable needed. The `else` belongs to the `for`, and runs "
            "because no `break` happened.",
        ),
    ),
    visualizations=(
        {
            "kind": "trace",
            "title": "Tracing a while loop",
            "code": "n = 3\nwhile n > 0:\n    print(n)\n    n -= 1",
            "steps": [
                {"line": 2, "state": {"n": 3}, "note": "3 > 0 → enter"},
                {"line": 4, "state": {"n": 2}, "note": "printed 3"},
                {"line": 4, "state": {"n": 1}, "note": "printed 2"},
                {"line": 4, "state": {"n": 0}, "note": "printed 1"},
                {"line": 2, "state": {"n": 0}, "note": "0 > 0 is false → exit"},
            ],
        },
    ),
    exercises=(
        ExerciseSpec(
            slug="loops-fizzbuzz",
            title="Classic: FizzBuzz",
            prompt="""\
Implement `fizzbuzz(n)` returning a **list** of `n` entries for 1..n:

* multiples of 3 and 5 → `"FizzBuzz"`
* multiples of 3 → `"Fizz"`
* multiples of 5 → `"Buzz"`
* anything else → the number as a **string**

`fizzbuzz(5)` → `["1", "2", "Fizz", "4", "Buzz"]`
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.BEGINNER,
            difficulty=0.35,
            estimated_minutes=10,
            starter_files={
                "main.py": '''\
def fizzbuzz(n: int) -> list[str]:
    """Return the FizzBuzz sequence from 1 to n inclusive."""
    ...
'''
            },
            hidden_files={
                "test_fizzbuzz.py": """\
from main import fizzbuzz


def test_first_five():
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]


def test_fizzbuzz_at_fifteen():
    assert fizzbuzz(15)[14] == "FizzBuzz"


def test_length_matches_n():
    assert len(fizzbuzz(100)) == 100


def test_all_entries_are_strings():
    assert all(isinstance(entry, str) for entry in fizzbuzz(20))


def test_zero_is_empty():
    assert fizzbuzz(0) == []
"""
            },
            concepts=("loops", "conditionals", "lists"),
            hints=(
                HintSpec(
                    "The order of your checks decides the answer. Which condition is the "
                    "most specific?"
                ),
                HintSpec(
                    "A number divisible by both 3 and 5 must be tested *before* the "
                    "individual checks, or it will match the first one and stop."
                ),
                HintSpec(
                    "`n % 3 == 0` tests divisibility by 3. Note the range must run from "
                    "1 to n inclusive — `range(1, n + 1)`."
                ),
                HintSpec(
                    "```python\nout = []\nfor i in range(1, n + 1):\n"
                    '    if i % 15 == 0:\n        out.append("FizzBuzz")\n'
                    "    elif ...\n```\nRemember non-matching numbers become `str(i)`."
                ),
            ),
            solution_files={
                "main.py": '''\
def fizzbuzz(n: int) -> list[str]:
    """Return the FizzBuzz sequence from 1 to n inclusive."""
    result: list[str] = []
    for number in range(1, n + 1):
        if number % 15 == 0:
            result.append("FizzBuzz")
        elif number % 3 == 0:
            result.append("Fizz")
        elif number % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(number))
    return result
'''
            },
            solution_explanation="Divisible by 15 is the same as divisible by both 3 and 5, "
            "and testing it first is what makes the elif chain correct. `range(1, n + 1)` "
            "gives 1..n; note that `fizzbuzz(0)` then correctly returns an empty list without "
            "a special case.",
            misconception_rules=(
                {"pattern": "test_first_five", "misconception": "off-by-one"},
                {"pattern": "test_all_entries_are_strings", "misconception": "type-mismatch"},
            ),
        ),
        ExerciseSpec(
            slug="loops-debug-infinite",
            title="Debug: the loop that never ends",
            prompt="""\
`countdown(start)` should return a list counting down to 1, e.g.
`countdown(3)` → `[3, 2, 1]`.

It currently hangs. Find out why and fix it — without changing the function
signature or the return type.

*This exercise runs against the sandbox timeout. A hang will be reported as a
timeout, not a crash: that is itself the diagnostic clue.*
""",
            kind=ExerciseKind.DEBUG,
            level=SkillLevel.BEGINNER,
            difficulty=0.4,
            estimated_minutes=8,
            xp_reward=35,
            starter_files={
                "main.py": '''\
def countdown(start: int) -> list[int]:
    """Return [start, start-1, ..., 1]."""
    numbers = []
    current = start
    while current > 0:
        numbers.append(current)
    return numbers
'''
            },
            hidden_files={
                "test_countdown.py": """\
from main import countdown


def test_counts_down():
    assert countdown(3) == [3, 2, 1]


def test_one():
    assert countdown(1) == [1]


def test_zero_is_empty():
    assert countdown(0) == []


def test_larger():
    assert countdown(100)[0] == 100
    assert countdown(100)[-1] == 1
    assert len(countdown(100)) == 100
"""
            },
            concepts=("loops", "debugging"),
            hints=(
                HintSpec(
                    "Ask the question every while loop must answer: what changes inside "
                    "the body, and what eventually makes the condition false?"
                ),
                HintSpec(
                    "`current` is compared in the condition. Trace it: what is its value "
                    "on pass 1? On pass 2?"
                ),
                HintSpec(
                    "Nothing ever modifies `current`, so `current > 0` stays true for "
                    "ever. The list grows until memory or the timeout runs out."
                ),
                HintSpec("Add `current -= 1` as the last statement inside the loop body."),
            ),
            solution_files={
                "main.py": '''\
def countdown(start: int) -> list[int]:
    """Return [start, start-1, ..., 1]."""
    numbers: list[int] = []
    current = start
    while current > 0:
        numbers.append(current)
        current -= 1
    return numbers
'''
            },
            solution_explanation="The loop variable must move toward the exit condition. A "
            "`for number in range(start, 0, -1)` loop would make the termination structural "
            "rather than something you have to remember — which is why `for` is preferred "
            "whenever the range is known in advance.",
            misconception_rules=({"pattern": "timeout|Timeout", "misconception": "infinite-loop"},),
        ),
    ),
)

FOUNDATIONS_MODULE = ModuleSpec(
    slug="foundations",
    title="Foundations: How Python Thinks",
    summary="The execution model, names and objects, decisions and repetition. Everything "
    "else in the curriculum assumes this module.",
    level=SkillLevel.BEGINNER,
    lessons=(PYTHON_FUNDAMENTALS, VARIABLES_AND_TYPES, CONDITIONS, LOOPS),
)
