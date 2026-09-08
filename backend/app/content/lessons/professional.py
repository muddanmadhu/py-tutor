"""Module 05–06: object orientation, files, APIs, testing and automation.

This is where a learner stops writing scripts and starts writing software that
other people run.
"""

from __future__ import annotations

from app.content.schema import Example, ExerciseSpec, HintSpec, LessonSpec, ModuleSpec
from app.models.enums import ExerciseKind, SkillLevel

# ---------------------------------------------------------------------------
# Lesson 9 — OOP
# ---------------------------------------------------------------------------

OOP = LessonSpec(
    slug="object-oriented-programming",
    title="Classes: Bundling State With Behaviour",
    summary="__init__, methods, properties, inheritance, dunder methods — and when a "
    "function would have been better.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=35,
    xp_reward=35,
    concepts=("classes", "inheritance", "dunder-methods", "dataclasses"),
    reference_keys=("dataclasses.dataclass", "property", "isinstance"),
    body="""\
## A class is a template for objects

```python
class Account:
    \"\"\"A bank account with a balance that cannot go negative.\"\"\"

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        self.owner = owner
        self._balance = balance          # leading underscore: internal by convention

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError(f"deposit must be positive, got {amount}")
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        if amount > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount

    @property
    def balance(self) -> float:
        \"\"\"Read-only view of the balance.\"\"\"
        return self._balance
```

`__init__` is not a constructor — the object already exists by then. It is the
*initialiser*: its job is to establish the invariants the rest of the class
relies on. Here the invariant is "balance is never negative", and every method
is written to preserve it.

`self` is the instance the method was called on. `account.deposit(50)` is
`Account.deposit(account, 50)`. Nothing magic; the syntax just moves the first
argument in front of the dot.

## Instance, class and static

```python
class Order:
    tax_rate = 0.2                       # class attribute — one, shared

    def __init__(self, total):
        self.total = total               # instance attribute — one per object

    def with_tax(self):                  # instance method: needs this order
        return self.total * (1 + self.tax_rate)

    @classmethod
    def from_json(cls, payload):         # alternative constructor
        return cls(total=payload["total"])

    @staticmethod
    def is_valid_total(value):           # related utility; needs neither
        return isinstance(value, int | float) and value >= 0
```

`@classmethod` receives the class, and is how you write alternative
constructors that keep working in subclasses. `@staticmethod` receives nothing —
it is a plain function that lives in the class's namespace because that is where
readers will look for it.

Watch the shared-class-attribute trap:

```python
class Basket:
    items = []          # ← shared by EVERY basket
```

Mutating `self.items` mutates it for all instances. Per-instance state goes in
`__init__`.

## Properties

`@property` turns a method into a computed attribute. Use it to add validation
or derivation *without* changing the call site:

```python
@property
def celsius(self) -> float:
    return self._celsius

@celsius.setter
def celsius(self, value: float) -> None:
    if value < -273.15:
        raise ValueError("below absolute zero")
    self._celsius = value
```

Python has no `private`. The convention is `_name` for internal and `__name` for
name-mangled. Both are advisory. The community relies on documentation and
discipline rather than enforcement, which works better than you would expect.

## Inheritance, and why composition usually wins

```python
class Animal:
    def speak(self) -> str:
        raise NotImplementedError

class Dog(Animal):
    def speak(self) -> str:
        return "Woof"

class Cat(Animal):
    def speak(self) -> str:
        return "Meow"

for animal in [Dog(), Cat()]:
    print(animal.speak())          # polymorphism: same call, different behaviour
```

Inheritance says *is-a* and couples the subclass to the parent's internals
permanently. Composition says *has-a* and stays flexible:

```python
class Report:
    def __init__(self, formatter):     # inject the behaviour
        self.formatter = formatter
```

Prefer composition. Reach for inheritance when there is a genuine "is-a" with a
stable base — and when you find yourself overriding most of the parent, that is
the signal you wanted composition.

`super().__init__(...)` calls up the chain. Always call it: skipping it leaves
the parent's invariants unestablished.

## Dunder methods

```python
class Money:
    def __init__(self, pence: int) -> None:
        self.pence = pence

    def __repr__(self) -> str:          # for developers/debuggers
        return f"Money(pence={self.pence})"

    def __str__(self) -> str:           # for users
        return f"£{self.pence / 100:.2f}"

    def __eq__(self, other) -> bool:
        return isinstance(other, Money) and self.pence == other.pence

    def __lt__(self, other) -> bool:
        return self.pence < other.pence

    def __add__(self, other):
        return Money(self.pence + other.pence)

    def __hash__(self) -> int:          # define whenever you define __eq__
        return hash(self.pence)
```

Define `__repr__` on every class you write. It costs one line and it is what you
see in a debugger, a log line and a failing test. The default
`<Money object at 0x7f…>` tells you nothing.

If you define `__eq__` and want instances usable in sets or as dict keys, define
`__hash__` too — Python sets it to None otherwise.

## Dataclasses remove the boilerplate

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
```

You get `__init__`, `__repr__` and `__eq__` for free. `frozen=True` makes it
immutable and hashable; `slots=True` removes the per-instance dict, cutting
memory and speeding up attribute access. For value objects this should be your
default.
""",
    sections={
        "what_is_it": "A class defines a type: what data its instances hold and what "
        "operations they support. An object is one instance of that type.",
        "why_it_exists": "To keep state and the operations that maintain it in one place. "
        "When the invariants of some data are enforced in five different functions, they will "
        "eventually disagree.",
        "how_it_works": "`class` creates a class object. Calling it allocates an instance "
        "(`__new__`) and initialises it (`__init__`). Attribute lookup walks the instance "
        "dict, then the class, then the MRO of its bases. Methods are functions found on the "
        "class and bound to the instance on access.",
        "when_to_use": "When data and behaviour belong together and there are invariants to "
        "protect; when you need several instances with independent state; when polymorphism "
        "lets callers stay ignorant of concrete types.",
        "when_not_to_use": "A class with one method and no state is a function wearing a "
        "costume. A class that only holds data is a dataclass or a NamedTuple. Deep "
        "inheritance hierarchies are almost always a mistake.",
        "common_mistakes": "Forgetting `self`; mutable class attributes shared across "
        "instances; no `__repr__`; defining `__eq__` without `__hash__`; forgetting "
        "`super().__init__()`; using inheritance for code reuse rather than for an is-a "
        "relationship.",
        "real_world": "ORM models, API clients, service classes, page objects in test "
        "automation, and configuration objects. In automation frameworks the page-object "
        "pattern is pure OOP: state (the page) plus behaviour (the interactions).",
        "alternatives": "Plain functions with explicit arguments; dataclasses/NamedTuples "
        "for data; closures for a single piece of captured state; modules for singletons; "
        "protocols (structural typing) instead of an inheritance hierarchy.",
        "performance": "Attribute access on an instance goes through a dict, so it is slower "
        "than a local variable. `__slots__` (or `@dataclass(slots=True)`) removes that dict, "
        "saving memory and time when you have many instances. Do not build a class per row of "
        "a million-row dataset without measuring.",
        "security": "Do not put secrets in attributes that end up in `__repr__` — they will "
        "be logged. Be careful with `__eq__` on credential objects: use `hmac.compare_digest` "
        "for anything comparing secrets, to avoid timing leaks.",
    },
    starter_code='''\
from dataclasses import dataclass


@dataclass
class Book:
    """A book in a library catalogue."""

    title: str
    author: str
    year: int

    def citation(self) -> str:
        """Return a short citation string."""
        return f"{self.author} ({self.year}). {self.title}."


book = Book("The Pragmatic Programmer", "Hunt & Thomas", 1999)
print(book)
print(book.citation())
''',
    examples=(
        Example(
            title="__repr__ is the one you must not skip",
            code="""\
class Silent:
    def __init__(self, value):
        self.value = value


class Helpful:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Helpful(value={self.value!r})"


print([Silent(1), Silent(2)])
print([Helpful(1), Helpful(2)])
""",
            output="[<__main__.Silent object at 0x...>, <__main__.Silent object at 0x...>]\n"
            "[Helpful(value=1), Helpful(value=2)]",
            explanation="The first line is what a failing test looks like without `__repr__`. "
            "The second is what it looks like with one.",
        ),
        Example(
            title="The shared class attribute trap",
            code="""\
class Broken:
    items = []          # shared

    def add(self, x):
        self.items.append(x)


class Fixed:
    def __init__(self):
        self.items = []  # per instance

    def add(self, x):
        self.items.append(x)


a, b = Broken(), Broken()
a.add(1)
print("broken:", b.items)

c, d = Fixed(), Fixed()
c.add(1)
print("fixed: ", d.items)
""",
            output="broken: [1]\nfixed:  []",
            explanation="`b` never had anything added to it. Same class-level list, same bug "
            "shape as the mutable default argument.",
        ),
        Example(
            title="Polymorphism without inheritance (duck typing)",
            code="""\
class JsonExporter:
    def export(self, rows):
        return f"exported {len(rows)} rows as JSON"


class CsvExporter:
    def export(self, rows):
        return f"exported {len(rows)} rows as CSV"


def run(exporter, rows):
    return exporter.export(rows)     # no common base class needed


print(run(JsonExporter(), [1, 2, 3]))
print(run(CsvExporter(), [1, 2]))
""",
            output="exported 3 rows as JSON\nexported 2 rows as CSV",
            explanation="Python cares that the object has an `export` method, not what it "
            "inherits from. `typing.Protocol` lets you type-check this without inheritance.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="oop-inventory-item",
            title="An inventory item that protects its invariants",
            prompt="""\
Build a class `InventoryItem` with:

* `__init__(self, sku, name, quantity=0, unit_price=0.0)`
* a read-only `total_value` property → quantity × unit_price
* `restock(amount)` — increase quantity; raise `ValueError` if amount ≤ 0
* `sell(amount)` — decrease quantity; raise `ValueError` if amount ≤ 0 or if
  there is not enough stock
* `__repr__` returning exactly `InventoryItem(sku='A1', quantity=5)`
* `__eq__` — two items are equal when their SKUs match
* quantity must never be negative, whatever the caller does
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.6,
            estimated_minutes=22,
            xp_reward=50,
            starter_files={
                "main.py": '''\
class InventoryItem:
    """A stock-keeping unit with a quantity that can never go negative."""

    def __init__(self, sku: str, name: str, quantity: int = 0,
                 unit_price: float = 0.0) -> None:
        ...
'''
            },
            hidden_files={
                "test_inventory.py": """\
import pytest

from main import InventoryItem


def make():
    return InventoryItem("A1", "Widget", quantity=5, unit_price=2.0)


def test_total_value():
    assert make().total_value == 10.0


def test_total_value_is_read_only():
    item = make()
    with pytest.raises(AttributeError):
        item.total_value = 999


def test_restock():
    item = make()
    item.restock(3)
    assert item.quantity == 8


def test_restock_rejects_non_positive():
    item = make()
    with pytest.raises(ValueError):
        item.restock(0)
    with pytest.raises(ValueError):
        item.restock(-1)


def test_sell():
    item = make()
    item.sell(2)
    assert item.quantity == 3


def test_cannot_oversell():
    item = make()
    with pytest.raises(ValueError):
        item.sell(6)
    assert item.quantity == 5, "a failed sale must not change the quantity"


def test_repr():
    assert repr(make()) == "InventoryItem(sku='A1', quantity=5)"


def test_equality_by_sku():
    assert InventoryItem("A1", "Widget") == InventoryItem("A1", "Different name")
    assert InventoryItem("A1", "Widget") != InventoryItem("B2", "Widget")


def test_equality_with_other_types():
    assert make() != "A1"


def test_instances_are_independent():
    first, second = make(), make()
    first.restock(10)
    assert second.quantity == 5
"""
            },
            concepts=("classes", "dunder-methods", "exceptions"),
            hints=(
                HintSpec(
                    "Set every instance attribute inside `__init__` — never in the class "
                    "body, or all your items will share it."
                ),
                HintSpec(
                    "A `@property` with no setter is read-only: assigning to it raises "
                    "AttributeError, which is exactly what one test checks."
                ),
                HintSpec(
                    "Validate *before* mutating. `test_cannot_oversell` asserts the "
                    "quantity is unchanged after a failed sale, so the check must come "
                    "first and the raise must happen before the subtraction."
                ),
                HintSpec(
                    "For `__eq__`, guard the type first:\n```python\ndef __eq__(self, other):\n"
                    "    if not isinstance(other, InventoryItem):\n"
                    "        return NotImplemented\n    return self.sku == other.sku\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
class InventoryItem:
    """A stock-keeping unit with a quantity that can never go negative.

    The invariant — ``quantity >= 0`` — is established in ``__init__`` and
    preserved by every mutating method, each of which validates before it
    changes anything.
    """

    def __init__(
        self,
        sku: str,
        name: str,
        quantity: int = 0,
        unit_price: float = 0.0,
    ) -> None:
        if quantity < 0:
            raise ValueError(f"quantity cannot start negative, got {quantity}")
        self.sku = sku
        self.name = name
        self.quantity = quantity
        self.unit_price = unit_price

    @property
    def total_value(self) -> float:
        """Value of the stock on hand. Derived, so it can never drift."""
        return self.quantity * self.unit_price

    def restock(self, amount: int) -> None:
        """Increase the quantity on hand."""
        if amount <= 0:
            raise ValueError(f"restock amount must be positive, got {amount}")
        self.quantity += amount

    def sell(self, amount: int) -> None:
        """Decrease the quantity on hand.

        Validates before mutating so a rejected sale leaves the item untouched.
        """
        if amount <= 0:
            raise ValueError(f"sale amount must be positive, got {amount}")
        if amount > self.quantity:
            raise ValueError(
                f"cannot sell {amount} of {self.sku}: only {self.quantity} in stock"
            )
        self.quantity -= amount

    def __repr__(self) -> str:
        return f"InventoryItem(sku={self.sku!r}, quantity={self.quantity})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InventoryItem):
            return NotImplemented
        return self.sku == other.sku

    def __hash__(self) -> int:
        # Defined alongside __eq__ so items stay usable in sets and dict keys.
        return hash(self.sku)
'''
            },
            solution_explanation="Three things worth taking away. **Validate before you "
            "mutate**, so a rejected operation leaves the object exactly as it was — "
            "half-applied changes are how corrupt state happens. **Derive rather than store**: "
            "`total_value` is a property, so it can never disagree with quantity and price. "
            "**Return `NotImplemented`** (not False) from `__eq__` for unknown types: that "
            "lets Python try the reflected operation before deciding they are unequal.",
            misconception_rules=(
                {
                    "pattern": "failed sale must not change",
                    "misconception": "mutate-before-validate",
                },
                {
                    "pattern": "test_instances_are_independent",
                    "misconception": "class-attribute-shared",
                },
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 10 — File handling
# ---------------------------------------------------------------------------

FILE_HANDLING = LessonSpec(
    slug="file-handling",
    title="Files, Paths and Data Formats",
    summary="Context managers, pathlib, JSON and CSV — reading and writing without losing "
    "data or leaking handles.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=30,
    xp_reward=30,
    concepts=("file-io", "json-data", "csv-data"),
    reference_keys=("open", "pathlib.Path", "json.load", "csv.DictReader"),
    body="""\
## Always use `with`

```python
with open("data.txt", encoding="utf-8") as handle:
    content = handle.read()
# the file is closed here — even if an exception was raised inside the block
```

Without `with`, an exception between `open` and `close` leaks the handle and can
lose buffered writes. `with` is not a style preference; it is the correctness
requirement.

Always pass `encoding="utf-8"` explicitly. The default depends on the platform's
locale, so code that works on your laptop can mangle text in the container.

## Modes

| Mode | Meaning | If the file exists | If it does not |
| --- | --- | --- | --- |
| `"r"` | read text (default) | reads | `FileNotFoundError` |
| `"w"` | write text | **truncates to empty** | creates |
| `"a"` | append text | appends at the end | creates |
| `"x"` | exclusive create | `FileExistsError` | creates |
| `"rb"` / `"wb"` | binary | as above | as above |

`"w"` destroys the existing contents the moment the file is opened, before you
write a single byte. If you cannot afford that, use `"x"` and handle the error.

## pathlib, not string concatenation

```python
from pathlib import Path

data_dir = Path("data")
target = data_dir / "reports" / "2026-09.csv"     # correct separators everywhere

target.exists()
target.suffix          # '.csv'
target.stem            # '2026-09'
target.parent          # Path('data/reports')
target.parent.mkdir(parents=True, exist_ok=True)

target.write_text("a,b\\n1,2\\n", encoding="utf-8")
text = target.read_text(encoding="utf-8")

for csv_file in Path("data").rglob("*.csv"):
    print(csv_file)
```

`Path` handles separators, gives you real methods instead of `os.path` function
calls, and makes the intent obvious.

## Reading large files

```python
with open("huge.log", encoding="utf-8") as handle:
    for line in handle:              # streams, one line at a time
        process(line)
```

`handle.read()` loads the whole file into memory. On a 4 GB log that is a
process-killer. Iterating the handle streams it in constant memory.

## JSON

```python
import json

data = json.loads('{"name": "Ada"}')          # from a string
text = json.dumps(data, indent=2)             # to a string

with open("config.json", encoding="utf-8") as handle:
    config = json.load(handle)                # from a file

with open("out.json", "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)         # to a file
```

Remember: `loads`/`dumps` take and return **s**trings; `load`/`dump` take a file
object. The mapping is narrow — JSON has no date, no tuple, no set. Datetimes go
in as ISO strings and come back as strings; converting them back is your job.

Anything can fail:

```python
try:
    config = json.loads(raw)
except json.JSONDecodeError as exc:
    raise ConfigError(f"invalid JSON at line {exc.lineno}") from exc
```

## CSV

```python
import csv

with open("sales.csv", newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        print(row["product"], row["amount"])   # every value is a str

with open("out.csv", "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["product", "amount"])
    writer.writeheader()
    writer.writerows(rows)
```

Two things bite people. `newline=""` is required — without it you get blank rows
between records on Windows. And **CSV has no types**: `row["amount"]` is the
string `"42"`, not the integer 42. Convert at the boundary.

Never parse CSV by `line.split(",")`. A single quoted field containing a comma
breaks it, and real-world CSV is full of them.

## Writing safely

A process killed mid-write leaves a half-written file that looks valid. Write to
a temporary file and rename — rename is atomic on POSIX:

```python
temp = target.with_suffix(".tmp")
temp.write_text(payload, encoding="utf-8")
temp.replace(target)          # atomic: readers see the old file or the new one
```
""",
    sections={
        "what_is_it": "File I/O is reading and writing persistent storage; pathlib models "
        "filesystem paths as objects; json and csv translate between text formats and Python "
        "objects.",
        "why_it_exists": "Programs need state that outlives the process, and need to exchange "
        "data with systems that do not share their memory.",
        "how_it_works": "`open()` returns a file object wrapping an OS handle with a buffer. "
        "`with` guarantees the handle is closed and the buffer flushed. Text mode encodes and "
        "decodes; binary mode does not touch the bytes.",
        "when_to_use": "Configuration, logs, reports, data interchange, caches, and anything "
        "another program will read.",
        "when_not_to_use": "For structured data queried by many processes, use a database — "
        "files have no transactions and no concurrent-write story. For data that must not be "
        "lost, files without fsync are not durable. For huge tabular data, use a columnar "
        "format (Parquet) rather than CSV.",
        "common_mistakes": "Not using `with`; forgetting `encoding='utf-8'`; opening with "
        "`'w'` and destroying data; building paths with `+`; loading a huge file with "
        "`.read()`; forgetting `newline=''` for CSV; assuming CSV values are typed; "
        "splitting CSV on commas.",
        "real_world": "Batch jobs read an input directory, process each file, write results "
        "and move the input to an archive folder. The production requirements are always the "
        "same: idempotency (safe to re-run), atomic writes, and never deleting the input "
        "until the output is durable.",
        "alternatives": "`sqlite3` for queryable local state; Parquet for large tables; "
        "`shelve`/`pickle` for Python-only persistence (never for untrusted data); object "
        "storage (S3) for anything distributed; `configparser`/`tomllib` for configuration.",
        "performance": "I/O dominates. Read line by line rather than loading everything; "
        "batch small writes rather than writing per record; the csv module is C-accelerated "
        "and beats manual parsing. For very large tabular work, Polars or PyArrow read "
        "an order of magnitude faster than the csv module.",
        "security": "Never build a path from user input without validating it — "
        "`Path(base) / user_input` still escapes with `../`. Resolve and check containment: "
        "`resolved.is_relative_to(base)`. Never `pickle.load` untrusted data: it executes "
        "arbitrary code. Watch for zip-bombs and unbounded reads from network sources.",
    },
    starter_code="""\
import json
from pathlib import Path

target = Path("report.json")
payload = {"generated": "2026-09-06", "rows": 3, "ok": True}

target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

loaded = json.loads(target.read_text(encoding="utf-8"))
print(loaded)
print("rows:", loaded["rows"])
""",
    examples=(
        Example(
            title="Streaming a file instead of loading it",
            code="""\
from pathlib import Path

Path("sample.log").write_text("INFO ok\\nERROR bad\\nINFO fine\\nERROR worse\\n",
                              encoding="utf-8")

errors = 0
with open("sample.log", encoding="utf-8") as handle:
    for line in handle:
        if line.startswith("ERROR"):
            errors += 1

print("errors:", errors)
""",
            output="errors: 2",
            explanation="Memory use is one line, whether the file is 4 KB or 4 GB.",
        ),
        Example(
            title="CSV values are strings",
            code="""\
import csv
import io

raw = "product,amount\\nWidget,42\\nGadget,7\\n"
reader = csv.DictReader(io.StringIO(raw))
rows = list(reader)

print(rows[0])
print("naive sum:", rows[0]["amount"] + rows[1]["amount"])
print("real sum: ", sum(int(row["amount"]) for row in rows))
""",
            output="{'product': 'Widget', 'amount': '42'}\nnaive sum: 427\nreal sum:  49",
            explanation="`'42' + '7'` is string concatenation. Convert at the boundary, once, "
            "rather than everywhere the value is used.",
        ),
        Example(
            title="Path traversal, and the check that stops it",
            code="""\
from pathlib import Path

base = Path("/srv/uploads").resolve()

for candidate in ["report.pdf", "../../etc/passwd"]:
    target = (base / candidate).resolve()
    safe = target.is_relative_to(base)
    print(f"{candidate!r:24} -> {'allowed' if safe else 'REJECTED'}")
""",
            output="'report.pdf'             -> allowed\n'../../etc/passwd'       -> REJECTED",
            explanation="Joining with `/` does not prevent traversal. Resolve, then check "
            "containment — that is the only reliable test.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="files-sales-report",
            title="Summarise a CSV into JSON",
            prompt="""\
Implement `summarise_sales(csv_path, json_path)`.

The CSV has the header `product,region,amount`. Write a JSON file containing:

```json
{
  "total_amount": 1234.5,
  "row_count": 42,
  "by_product": {"Widget": 900.0, "Gadget": 334.5},
  "top_product": "Widget"
}
```

Requirements:
* amounts are floats; skip any row whose amount will not parse, and count the
  skipped rows under `"skipped_rows"`
* `by_product` totals are rounded to 2 decimal places
* `top_product` is the highest total, ties broken alphabetically
* an empty CSV (header only) produces zeros, an empty `by_product` and
  `top_product: null` — it must not crash
* return the summary dict as well as writing it
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.65,
            estimated_minutes=25,
            xp_reward=55,
            starter_files={
                "main.py": '''\
import csv
import json
from pathlib import Path


def summarise_sales(csv_path: str, json_path: str) -> dict:
    """Read a sales CSV and write a JSON summary."""
    ...
'''
            },
            hidden_files={
                "test_sales.py": '''\
import json
from pathlib import Path

from main import summarise_sales

CSV = """product,region,amount
Widget,North,100.00
Gadget,South,50.50
Widget,South,200.00
Broken,East,not-a-number
Gadget,North,49.50
"""


def write_csv(tmp_path, content=CSV):
    path = tmp_path / "sales.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_totals(tmp_path):
    out = tmp_path / "summary.json"
    result = summarise_sales(str(write_csv(tmp_path)), str(out))
    assert result["total_amount"] == 400.0
    assert result["row_count"] == 4


def test_skipped_rows_counted(tmp_path):
    out = tmp_path / "summary.json"
    result = summarise_sales(str(write_csv(tmp_path)), str(out))
    assert result["skipped_rows"] == 1


def test_by_product(tmp_path):
    out = tmp_path / "summary.json"
    result = summarise_sales(str(write_csv(tmp_path)), str(out))
    assert result["by_product"] == {"Widget": 300.0, "Gadget": 100.0}


def test_top_product(tmp_path):
    out = tmp_path / "summary.json"
    result = summarise_sales(str(write_csv(tmp_path)), str(out))
    assert result["top_product"] == "Widget"


def test_writes_valid_json(tmp_path):
    out = tmp_path / "summary.json"
    summarise_sales(str(write_csv(tmp_path)), str(out))
    written = json.loads(Path(out).read_text(encoding="utf-8"))
    assert written["row_count"] == 4


def test_empty_csv(tmp_path):
    out = tmp_path / "summary.json"
    result = summarise_sales(
        str(write_csv(tmp_path, "product,region,amount\\n")), str(out)
    )
    assert result["row_count"] == 0
    assert result["total_amount"] == 0
    assert result["by_product"] == {}
    assert result["top_product"] is None
'''
            },
            concepts=("file-io", "csv-data", "json-data", "dictionaries"),
            hints=(
                HintSpec(
                    "Four stages: read the rows, convert and tally, decide the top "
                    "product, write the JSON. Write them as four blocks in one function "
                    "before worrying about elegance."
                ),
                HintSpec(
                    "`csv.DictReader` gives you a dict per row with string values. "
                    "Converting with `float(row['amount'])` can raise ValueError — that "
                    "is the row you skip and count."
                ),
                HintSpec(
                    "`max(totals, key=totals.get)` gives the highest, but not the "
                    "alphabetical tie-break. `max(totals.items(), key=lambda kv: "
                    "(kv[1], ...))` cannot break ties ascending either — sort instead."
                ),
                HintSpec(
                    "For the tie-break:\n```python\ntop = None\nif by_product:\n"
                    "    top = sorted(by_product.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]\n"
                    "```\nAnd remember `newline=''` when opening the CSV."
                ),
            ),
            solution_files={
                "main.py": '''\
import csv
import json
from pathlib import Path


def summarise_sales(csv_path: str, json_path: str) -> dict:
    """Read a sales CSV and write a JSON summary.

    Rows whose amount cannot be parsed are skipped and counted rather than
    aborting the run: one bad row in a nightly export should not lose the other
    fifty thousand.
    """
    totals: dict[str, float] = {}
    total_amount = 0.0
    row_count = 0
    skipped_rows = 0

    with open(csv_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                amount = float(row["amount"])
            except (TypeError, ValueError):
                skipped_rows += 1
                continue
            product = row["product"]
            totals[product] = round(totals.get(product, 0.0) + amount, 2)
            total_amount += amount
            row_count += 1

    top_product = None
    if totals:
        top_product = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[0][0]

    summary = {
        "total_amount": round(total_amount, 2),
        "row_count": row_count,
        "skipped_rows": skipped_rows,
        "by_product": totals,
        "top_product": top_product,
    }

    Path(json_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
'''
            },
            solution_explanation="The design decision worth noticing is what happens to the "
            "bad row. Crashing would lose the whole run; silently dropping it would hide a "
            "data-quality problem. Counting skipped rows in the output does neither — the job "
            "completes *and* the anomaly is visible to whoever reads the summary. That "
            "pattern — degrade, but report — is most of what makes a batch job production-grade.",
            misconception_rules=(
                {"pattern": "test_empty_csv", "misconception": "unhandled-empty-input"},
                {"pattern": "ValueError", "misconception": "value-conversion"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 11 — APIs
# ---------------------------------------------------------------------------

APIS = LessonSpec(
    slug="apis-and-http",
    title="APIs and HTTP: Talking to Other Systems",
    summary="Requests, status codes, authentication, timeouts, retries and pagination — the "
    "difference between a demo client and one you can run unattended.",
    level=SkillLevel.PROFESSIONAL,
    estimated_minutes=35,
    xp_reward=40,
    concepts=("http-basics", "api-clients", "json-data"),
    reference_keys=("requests.get", "json.loads", "urllib.request.urlopen"),
    body="""\
## The request/response model

```
CLIENT                                     SERVER
  │  GET /api/users/42 HTTP/1.1              │
  │  Host: api.example.com                   │
  │  Authorization: Bearer eyJ…              │
  │  Accept: application/json                │
  ├─────────────────────────────────────────►│
  │                                          │
  │  HTTP/1.1 200 OK                         │
  │  Content-Type: application/json          │
  │                                          │
  │  {"id": 42, "name": "Ada"}               │
  │◄─────────────────────────────────────────┤
```

HTTP is stateless: every request carries everything the server needs. That is
why the token goes on every call, not just at "login".

## Methods and what they promise

| Method | Purpose | Safe? | Idempotent? |
| --- | --- | --- | --- |
| GET | read | yes | yes |
| POST | create / trigger | no | **no** |
| PUT | replace entirely | no | yes |
| PATCH | partial update | no | usually |
| DELETE | remove | no | yes |

Idempotency is the property that matters for automation: sending the same
request twice has the same effect as sending it once. It is why you can safely
retry a PUT after a timeout, and why retrying a POST may create two orders.
When you must retry a POST, send an idempotency key.

## Status codes

```
2xx  success        200 OK   201 Created   204 No Content
3xx  redirection    301      304 Not Modified
4xx  YOUR fault     400 Bad Request  401 Unauthorized  403 Forbidden
                    404 Not Found    409 Conflict      422 Unprocessable
                    429 Too Many Requests
5xx  THEIR fault    500 Internal Error  502 Bad Gateway  503 Unavailable
                    504 Gateway Timeout
```

The retry rule follows directly: **retry 5xx and 429; do not retry 4xx.** A 400
will be a 400 the second time too — retrying it just wastes the rate-limit
budget you will need.

401 means "who are you?" (bad or missing credentials). 403 means "I know who you
are and you may not" (authenticated but unauthorised). Confusing them sends you
debugging the wrong thing.

## A minimal correct call

```python
import requests

response = requests.get(
    "https://api.example.com/users/42",
    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    timeout=10,                      # ← never omit this
)
response.raise_for_status()          # turns 4xx/5xx into an exception
user = response.json()
```

**No timeout means no timeout.** The default in `requests` is to wait for ever;
one unresponsive server then hangs a worker indefinitely, and a pool of workers
disappears one by one. Every HTTP call in production code has a timeout.

## Retries with exponential backoff

```python
import random, time
import requests

RETRYABLE = {429, 500, 502, 503, 504}

def get_with_retry(url, *, headers=None, attempts=4, timeout=10):
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code in RETRYABLE:
                raise requests.HTTPError(f"retryable status {response.status_code}")
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            delay = (2 ** attempt) + random.uniform(0, 0.5)   # backoff + jitter
            time.sleep(delay)
    raise RuntimeError(f"giving up after {attempts} attempts") from last_error
```

The jitter is not decoration. Without it, every client that failed at the same
moment retries at the same moment, and the recovering server is knocked over
again — the thundering herd.

## Pagination

```python
def fetch_all(url, headers):
    items, page = [], 1
    while True:
        response = requests.get(url, params={"page": page, "per_page": 100},
                                headers=headers, timeout=10)
        response.raise_for_status()
        batch = response.json()["items"]
        if not batch:
            return items
        items.extend(batch)
        page += 1
        if page > 1000:                    # a bound, always
            raise RuntimeError("pagination did not terminate")
```

Never write an unbounded pagination loop. A server bug that keeps returning the
same page will otherwise run until it exhausts memory.

## Authentication, briefly

* **API key** — a static secret in a header. Simple; rotate it, never commit it.
* **Bearer / JWT** — a signed, expiring token. Check expiry and refresh *before*
  the call, not after a 401.
* **OAuth2 client credentials** — exchange id+secret for a short-lived token.

In all three cases the secret comes from the environment or a secrets manager.
A key in source control is a key that is public.
""",
    sections={
        "what_is_it": "HTTP is the request/response protocol the web runs on; a REST API "
        "exposes resources over it, usually exchanging JSON.",
        "why_it_exists": "It is the lingua franca between systems written in different "
        "languages, owned by different teams, running in different places.",
        "how_it_works": "A client opens a TCP (usually TLS) connection, sends a request line, "
        "headers and an optional body, and reads a status line, headers and a body. Each "
        "request is independent; state lives in tokens, cookies or the server's database.",
        "when_to_use": "Integrating with third-party services, splitting a system into "
        "services, exposing functionality to browsers and mobile clients, automating a SaaS "
        "product that has no other interface.",
        "when_not_to_use": "For high-volume internal RPC where gRPC is faster; for streaming "
        "or push where WebSockets or SSE fit better; for bulk data movement where a file "
        "export beats a million small requests; for anything needing transactional guarantees "
        "across services.",
        "common_mistakes": "No timeout; not checking the status code; retrying 4xx; retrying "
        "non-idempotent POSTs; no backoff (thundering herd); ignoring rate-limit headers; "
        "unbounded pagination loops; logging the Authorization header; parsing an error page "
        "as data.",
        "real_world": "An integration job typically authenticates, pages through a resource, "
        "transforms each record, writes to a database, and reports what it did. It runs "
        "unattended at 2am, so every failure mode has to be handled without a human present.",
        "alternatives": "`httpx` for async and HTTP/2; gRPC for typed internal RPC; GraphQL "
        "when clients need to shape their own payloads; message queues for asynchronous "
        "work; webhooks so the server tells you instead of you polling.",
        "performance": "Latency dominates. Reuse connections with a `requests.Session` "
        "(TLS handshakes are expensive); request only the fields you need; page in large "
        "batches; parallelise independent calls with a thread pool or `asyncio`; cache "
        "responses that carry ETags.",
        "security": "Always HTTPS, never disable certificate verification. Secrets from the "
        "environment, never in source or logs — and remember tracebacks can contain the "
        "request object. Validate and bound anything you receive before using it. Beware SSRF: "
        "never fetch a URL supplied by a user without an allowlist.",
    },
    starter_code='''\
"""The sandbox has no network access, so this models a client against a stub."""


class StubResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def fetch_user(client, user_id: int) -> dict:
    """Fetch one user, failing loudly on a non-2xx response."""
    response = client.get(f"/users/{user_id}", timeout=10)
    response.raise_for_status()
    return response.json()


class StubClient:
    def get(self, path: str, timeout: int) -> StubResponse:
        return StubResponse(200, {"id": 42, "name": "Ada", "path": path})


print(fetch_user(StubClient(), 42))
''',
    examples=(
        Example(
            title="Which failures are worth retrying",
            code="""\
RETRYABLE = {429, 500, 502, 503, 504}

for status in [200, 400, 401, 404, 429, 500, 503]:
    if status < 400:
        verdict = "success"
    elif status in RETRYABLE:
        verdict = "retry with backoff"
    else:
        verdict = "do not retry - fix the request"
    print(f"{status}: {verdict}")
""",
            output="200: success\n400: do not retry - fix the request\n"
            "401: do not retry - fix the request\n404: do not retry - fix the request\n"
            "429: retry with backoff\n500: retry with backoff\n503: retry with backoff",
            explanation="429 is retryable but special: honour the `Retry-After` header if the "
            "server sends one rather than guessing.",
        ),
        Example(
            title="Backoff with jitter",
            code="""\
import random

random.seed(7)
for attempt in range(5):
    delay = min(2 ** attempt, 30) + random.uniform(0, 0.5)
    print(f"attempt {attempt + 1}: sleep {delay:.2f}s")
""",
            output="attempt 1: sleep 1.16s\nattempt 2: sleep 2.02s\nattempt 3: sleep 4.21s\n"
            "attempt 4: sleep 8.44s\nattempt 5: sleep 16.11s",
            explanation="Doubling, capped, plus a random fraction so retries from many "
            "clients spread out instead of arriving together.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="apis-resilient-client",
            title="A client that survives a flaky server",
            prompt="""\
Implement `fetch_with_retry(client, path, *, attempts=3)`.

`client.get(path)` returns an object with `.status_code` and `.json()`.

Behaviour:
* 2xx → return `response.json()`
* a status in `{429, 500, 502, 503, 504}` → retry, up to `attempts` total tries
* any other 4xx → raise `ClientError` immediately, without retrying
* all attempts exhausted → raise `ServiceUnavailable`
* if `client.get` raises `TimeoutError`, treat it as retryable

Define `ApiError` as the base, with `ClientError` and `ServiceUnavailable`
subclassing it. Do not sleep — the tests must run fast.
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.PROFESSIONAL,
            difficulty=0.7,
            estimated_minutes=25,
            xp_reward=60,
            starter_files={
                "main.py": '''\
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class ApiError(Exception):
    """Base class for API failures."""


# Define ClientError and ServiceUnavailable here.


def fetch_with_retry(client, path: str, *, attempts: int = 3) -> dict:
    """GET `path`, retrying transient failures."""
    ...
'''
            },
            hidden_files={
                "test_client.py": '''\
import pytest

from main import ApiError, ClientError, ServiceUnavailable, fetch_with_retry


class Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class ScriptedClient:
    """Returns each scripted item in turn; items may be Responses or exceptions."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = 0

    def get(self, path):
        self.calls += 1
        item = self.script.pop(0) if self.script else Response(500)
        if isinstance(item, Exception):
            raise item
        return item


def test_success_first_time():
    client = ScriptedClient(Response(200, {"ok": True}))
    assert fetch_with_retry(client, "/x") == {"ok": True}
    assert client.calls == 1


def test_retries_then_succeeds():
    client = ScriptedClient(Response(503), Response(500), Response(200, {"ok": 1}))
    assert fetch_with_retry(client, "/x") == {"ok": 1}
    assert client.calls == 3


def test_client_error_is_not_retried():
    client = ScriptedClient(Response(404))
    with pytest.raises(ClientError):
        fetch_with_retry(client, "/missing")
    assert client.calls == 1, "4xx must not be retried"


def test_exhausted_retries():
    client = ScriptedClient(Response(500), Response(500), Response(500))
    with pytest.raises(ServiceUnavailable):
        fetch_with_retry(client, "/x", attempts=3)
    assert client.calls == 3


def test_timeout_is_retryable():
    client = ScriptedClient(TimeoutError("slow"), Response(200, {"ok": 2}))
    assert fetch_with_retry(client, "/x") == {"ok": 2}


def test_both_errors_share_a_base():
    assert issubclass(ClientError, ApiError)
    assert issubclass(ServiceUnavailable, ApiError)


def test_error_mentions_status():
    client = ScriptedClient(Response(403))
    with pytest.raises(ClientError) as info:
        fetch_with_retry(client, "/forbidden")
    assert "403" in str(info.value)
'''
            },
            concepts=("api-clients", "http-basics", "exceptions"),
            hints=(
                HintSpec(
                    "Three outcomes per attempt: success (return), retryable (loop "
                    "again), fatal (raise now). Write the loop around those three cases."
                ),
                HintSpec(
                    "`for attempt in range(attempts):` bounds the retries. Whether you "
                    "raise after the loop or on the last iteration, make sure the call "
                    "count is exactly `attempts`."
                ),
                HintSpec(
                    "The 4xx case must `raise` from *inside* the loop so the retry never "
                    "happens. Only the retryable branch should reach the next iteration. "
                    "Remember `client.get` itself can raise TimeoutError — wrap it."
                ),
                HintSpec(
                    "```python\nfor _ in range(attempts):\n    try:\n"
                    "        response = client.get(path)\n"
                    "    except TimeoutError:\n        continue\n"
                    "    if response.status_code < 300:\n        return response.json()\n"
                    "    if response.status_code not in RETRYABLE_STATUSES:\n"
                    "        raise ClientError(...)\nraise ServiceUnavailable(...)\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class ApiError(Exception):
    """Base class for API failures."""


class ClientError(ApiError):
    """The request itself was wrong; retrying will not help."""


class ServiceUnavailable(ApiError):
    """The service failed transiently and did not recover within our budget."""


def fetch_with_retry(client, path: str, *, attempts: int = 3) -> dict:
    """GET ``path``, retrying transient failures.

    Retries 429 and 5xx (and timeouts) because those may succeed on a second
    attempt. Never retries other 4xx: a malformed or unauthorised request will
    be malformed or unauthorised again, and retrying only burns the rate limit.

    A real client would sleep with exponential backoff and jitter between
    attempts; that is omitted here so the behaviour stays testable.
    """
    last_status: int | None = None

    for _ in range(attempts):
        try:
            response = client.get(path)
        except TimeoutError:
            last_status = None
            continue

        status = response.status_code
        if 200 <= status < 300:
            return response.json()
        if status not in RETRYABLE_STATUSES:
            raise ClientError(f"request to {path} failed with status {status}")
        last_status = status

    raise ServiceUnavailable(
        f"{path} did not succeed after {attempts} attempts "
        f"(last status: {last_status})"
    )
'''
            },
            solution_explanation="The important design point is the *asymmetry*: transient "
            "failures get another chance, permanent ones fail fast. Retrying a 404 or a 401 "
            "is not resilience — it is a slower way to get the same error while consuming "
            "your rate-limit budget. In production add exponential backoff with jitter "
            "between attempts, honour a `Retry-After` header on 429, and put the attempt "
            "count and last status in the log line so the failure is diagnosable without a "
            "reproduction.",
            misconception_rules=(
                {"pattern": "4xx must not be retried", "misconception": "retry-non-retryable"},
                {"pattern": "test_timeout_is_retryable", "misconception": "missing-timeout"},
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 12 — Testing
# ---------------------------------------------------------------------------

TESTING = LessonSpec(
    slug="testing",
    title="Testing: Proving It Works, and Keeping It Working",
    summary="pytest, arrange-act-assert, fixtures, parametrisation, mocking — and writing "
    "tests that survive a refactor.",
    level=SkillLevel.INTERMEDIATE,
    estimated_minutes=35,
    xp_reward=40,
    concepts=("unit-testing", "test-design", "debugging"),
    reference_keys=("pytest.raises", "unittest.mock.patch", "pytest.fixture"),
    body="""\
## What a test is for

A test is an executable claim about behaviour. Its real value is not proving the
code works today — you can do that by hand. It is that when someone changes the
code in six months, the claim is re-checked automatically.

That reframes everything: a test that breaks whenever you refactor is not
protecting you, it is taxing you.

## The shape: arrange, act, assert

```python
def test_withdraw_reduces_balance():
    account = Account("Ada", balance=100)     # arrange
    account.withdraw(30)                      # act
    assert account.balance == 70              # assert
```

One behaviour per test. When a test fails you should know what broke from the
name alone — `test_withdraw_reduces_balance` tells you; `test_account_2` does
not.

## pytest essentials

```python
import pytest

def test_plain_assert():
    assert add(2, 2) == 4          # pytest rewrites asserts to show both sides

def test_raises():
    with pytest.raises(ValueError, match="must be positive"):
        withdraw(-5)

@pytest.mark.parametrize(
    "amount,expected",
    [(1, 3.99), (10, 9.99), (25, 24.99), (5, 3.99)],   # boundary included
)
def test_shipping(amount, expected):
    assert shipping_cost(amount, False) == expected

def test_float_comparison():
    assert 0.1 + 0.2 == pytest.approx(0.3)
```

Parametrisation turns four near-identical tests into one, and each case is
reported separately, so a failure names the exact input.

## Fixtures

```python
@pytest.fixture
def account():
    return Account("Ada", balance=100)

@pytest.fixture
def temp_db(tmp_path):
    path = tmp_path / "test.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    yield connection            # the test runs here
    connection.close()          # teardown, guaranteed
```

`tmp_path` and `capsys` are built in: a per-test temporary directory, and
captured stdout/stderr. Use `tmp_path` rather than writing into the repository.

## What to test

Test **behaviour**, not implementation:

```python
# brittle — breaks when you rename an internal
assert account._balance == 70

# durable — describes what a caller can observe
assert account.balance == 70
```

And test the edges, because that is where the bugs are: empty input, one item,
the boundary value, one past the boundary, negative, zero, None, duplicates,
unicode, and the largest realistic size.

## Mocking, and its limits

Mock what you do not own and cannot control: network calls, the clock,
randomness, the filesystem when it is slow.

```python
from unittest.mock import patch, Mock

def test_fetch_user_handles_404():
    fake = Mock()
    fake.get.return_value = Mock(status_code=404)

    with pytest.raises(ClientError):
        fetch_user(fake, 42)

@patch("myapp.emailer.send")
def test_signup_sends_welcome(mock_send):
    signup("ada@example.com")
    mock_send.assert_called_once_with("ada@example.com", template="welcome")
```

Patch **where the name is looked up**, not where it is defined: if
`myapp.service` does `from myapp.emailer import send`, you patch
`myapp.service.send`. This is the single most common mocking mistake.

The limit: a test where everything is mocked tests your mocks. Mock at the
system boundary; use the real objects inside it.

## The pyramid

```
        ╱ E2E ╲          few, slow, brittle, highest confidence
      ╱─────────╲
    ╱ Integration ╲      some — real database, real HTTP against a stub server
  ╱─────────────────╲
╱     Unit tests      ╲  many, fast, isolated, run on every save
```

Aim for a suite that runs in seconds, so people actually run it. A five-minute
suite gets skipped, and a skipped suite protects nothing.

## Coverage is a floor, not a target

Coverage tells you which lines *ran*, not whether they were checked. This has
100% coverage and asserts nothing:

```python
def test_useless():
    calculate_everything()
```

Use coverage to find code nobody tested at all. Do not chase the last 5%; the
effort is better spent on the edge cases in the 95%.
""",
    sections={
        "what_is_it": "Automated tests are code that runs your code and asserts what it "
        "should do. Unit tests check one piece in isolation; integration tests check pieces "
        "together; end-to-end tests check the whole system.",
        "why_it_exists": "So that changing code is safe. Without tests, every change is a "
        "gamble, and the codebase becomes something people are afraid to touch.",
        "how_it_works": "pytest discovers `test_*.py` files and `test_*` functions, runs "
        "each in a fresh call, and reports failures with a rewritten assertion showing both "
        "sides. Fixtures supply and clean up dependencies.",
        "when_to_use": "Always for logic with branches or edge cases; always for bug fixes "
        "(write the failing test first — it proves the fix and prevents the regression); "
        "always at system boundaries.",
        "when_not_to_use": "Do not unit-test trivial getters, third-party library internals, "
        "or generated code. Do not write end-to-end tests for logic a unit test can cover — "
        "they are slower and flakier for the same information.",
        "common_mistakes": "Testing implementation details; one test asserting six unrelated "
        "things; tests that depend on execution order or on each other; over-mocking until "
        "nothing real is exercised; patching where a name is defined rather than where it is "
        "used; treating coverage as the goal.",
        "real_world": "CI runs the suite on every pull request; a red build blocks the merge. "
        "Bug reports become failing tests before they become fixes. Test automation engineers "
        "spend most of their time on the design of the suite — fixtures, data, isolation — "
        "not on individual assertions.",
        "alternatives": "`unittest` (stdlib, class-based); `hypothesis` for property-based "
        "testing that generates edge cases you would not think of; `doctest` for examples in "
        "docstrings; contract testing between services; type checking as a cheap partial "
        "substitute for a class of tests.",
        "performance": "Keep unit tests in milliseconds. Use `tmp_path` over real I/O, fake "
        "the clock rather than sleeping, run with `pytest -n auto` (xdist) to use every core, "
        "and keep expensive fixtures at session scope.",
        "security": "Never put real credentials in tests or fixtures — use obvious fakes. "
        "Never point tests at production. Include security cases in the suite: injection "
        "strings, oversized inputs, path traversal attempts. A regression test for a fixed "
        "vulnerability is how it stays fixed.",
    },
    starter_code='''\
"""Run this with the Test button — it runs pytest in the sandbox."""


def is_palindrome(text: str) -> bool:
    """Return True when `text` reads the same forwards and backwards."""
    cleaned = "".join(char.lower() for char in text if char.isalnum())
    return cleaned == cleaned[::-1]


def test_simple_palindrome():
    assert is_palindrome("racecar")


def test_ignores_case_and_punctuation():
    assert is_palindrome("A man, a plan, a canal: Panama")


def test_rejects_non_palindrome():
    assert not is_palindrome("python")


def test_empty_string_is_a_palindrome():
    assert is_palindrome("")
''',
    examples=(
        Example(
            title="Parametrisation replaces copy-paste",
            code="""\
import pytest


def grade(score):
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    return "F"


@pytest.mark.parametrize(
    "score,expected",
    [(95, "A"), (90, "A"), (89, "B"), (80, "B"), (79, "F"), (0, "F")],
)
def test_grade(score, expected):
    assert grade(score) == expected
""",
            output="6 passed",
            explanation="Every boundary is covered and each case is reported by name. Note "
            "90 and 80 are included: boundaries are where off-by-one lives.",
        ),
        Example(
            title="Patch where the name is used",
            code="""\
# service.py:  from emailer import send
#
# WRONG — patches the definition, which service.py no longer looks at
@patch("emailer.send")
#
# RIGHT — patches the name in the module under test
@patch("service.send")
def test_signup(mock_send):
    ...
""",
            output="",
            explanation="`from x import y` binds `y` into the importing module's namespace. "
            "Patching `x.y` afterwards does not change the binding the code actually uses.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="testing-find-the-bug",
            title="Write the tests that expose the bug",
            prompt="""\
`apply_discount(price, percent)` is in production and is losing money. You have
been told only that "some discounts come out wrong".

Write tests in `test_discount.py` that expose the defects. Your suite must:

* include at least 5 test functions
* pass against the *correct* implementation
* fail against the buggy one

You are not fixing the code. You are proving what is wrong — which is what you
do before touching anything in a live system.

Correct behaviour:
* returns the price after the percentage discount, rounded to 2 decimal places
* `percent` of 0 returns the price unchanged; 100 returns 0.0
* `percent` outside 0–100 raises `ValueError`
* a negative price raises `ValueError`
""",
            kind=ExerciseKind.TEST_WRITING,
            level=SkillLevel.INTERMEDIATE,
            difficulty=0.7,
            estimated_minutes=22,
            xp_reward=55,
            starter_files={
                "test_discount.py": '''\
"""Write tests that expose the defects in discount.apply_discount."""

import pytest

from discount import apply_discount


def test_no_discount_returns_original_price():
    assert apply_discount(100.0, 0) == 100.0


# Add at least four more tests below.
'''
            },
            hidden_files={
                "discount.py": '''\
"""The implementation under test — correct, so a good suite passes here."""


def apply_discount(price: float, percent: float) -> float:
    """Return `price` reduced by `percent`, rounded to 2 decimal places."""
    if price < 0:
        raise ValueError(f"price cannot be negative, got {price}")
    if not 0 <= percent <= 100:
        raise ValueError(f"percent must be between 0 and 100, got {percent}")
    return round(price * (1 - percent / 100), 2)
''',
                "test_meta.py": '''\
"""Grades the learner's suite: it must be substantial and must catch the bugs."""

import ast
import subprocess
import sys
from pathlib import Path

# A deliberately broken implementation: no validation, and `percent` is treated
# as a fraction rather than a percentage. A suite worth having fails against it.
BUGGY = "\\n".join(
    [
        "def apply_discount(price, percent):",
        "    return round(price * (1 - percent), 2)",
        "",
    ]
)


def _test_functions():
    tree = ast.parse(Path("test_discount.py").read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]


def test_suite_has_enough_tests():
    names = _test_functions()
    assert len(names) >= 5, f"write at least 5 tests, found {len(names)}: {names}"


def test_suite_checks_error_cases():
    source = Path("test_discount.py").read_text(encoding="utf-8")
    assert "pytest.raises" in source, (
        "the brief says invalid input must raise - assert that with pytest.raises"
    )


def test_suite_fails_against_the_buggy_implementation(tmp_path):
    """A suite that passes against broken code is not testing anything."""
    workspace = tmp_path / "buggy"
    workspace.mkdir()
    (workspace / "discount.py").write_text(BUGGY, encoding="utf-8")
    (workspace / "test_discount.py").write_text(
        Path("test_discount.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "test_discount.py"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0, (
        "your suite passes against a deliberately broken implementation - "
        "it is not asserting enough"
    )
''',
            },
            concepts=("unit-testing", "test-design", "debugging"),
            hints=(
                HintSpec(
                    "Start from the specification, not from the code. Each bullet in the "
                    "brief is at least one test."
                ),
                HintSpec(
                    "The brief mentions two error cases. `pytest.raises(ValueError)` is "
                    "how you assert that something raises."
                ),
                HintSpec(
                    "Think about the boundaries: 0%, 100%, and just outside the valid "
                    "range on both sides. Also test a percentage that produces a value "
                    "needing rounding — that is where a fraction-vs-percentage bug shows."
                ),
                HintSpec(
                    "A suite like this catches it:\n```python\ndef test_half_price():\n"
                    "    assert apply_discount(100.0, 50) == 50.0\n\n"
                    "def test_full_discount():\n    assert apply_discount(80.0, 100) == 0.0\n\n"
                    "def test_rejects_percent_over_100():\n"
                    "    with pytest.raises(ValueError):\n        apply_discount(10.0, 150)\n```"
                ),
            ),
            solution_files={
                "test_discount.py": '''\
"""Tests derived from the specification, not from the implementation."""

import pytest

from discount import apply_discount


def test_no_discount_returns_original_price():
    assert apply_discount(100.0, 0) == 100.0


def test_half_price():
    assert apply_discount(100.0, 50) == 50.0


def test_full_discount_is_free():
    assert apply_discount(80.0, 100) == 0.0


def test_rounds_to_two_decimal_places():
    # 33% off 19.99 is 13.3933, which must not leak extra precision into a price.
    assert apply_discount(19.99, 33) == 13.39


def test_rejects_percent_above_100():
    with pytest.raises(ValueError):
        apply_discount(10.0, 150)


def test_rejects_negative_percent():
    with pytest.raises(ValueError):
        apply_discount(10.0, -5)


def test_rejects_negative_price():
    with pytest.raises(ValueError):
        apply_discount(-1.0, 10)


def test_boundaries_are_inclusive():
    assert apply_discount(50.0, 0) == 50.0
    assert apply_discount(50.0, 100) == 0.0
'''
            },
            solution_explanation="Notice how the suite was built: one test per clause of the "
            "specification, then the boundaries (0 and 100 inclusive, just outside on both "
            "sides), then a rounding case. That is a repeatable method, and it is why the "
            "suite catches a percent-versus-fraction bug the author never anticipated — the "
            "test asserts what the *specification* says, not what the code happens to do.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Lesson 13 — Automation
# ---------------------------------------------------------------------------

AUTOMATION = LessonSpec(
    slug="automation",
    title="Automation: Code That Runs Without You",
    summary="Idempotency, structured logging, CLI design and failure handling for jobs that "
    "run at 2am with nobody watching.",
    level=SkillLevel.PROFESSIONAL,
    estimated_minutes=32,
    xp_reward=40,
    concepts=("automation-design", "logging", "cli-design", "security-basics"),
    reference_keys=("argparse.ArgumentParser", "logging.getLogger", "pathlib.Path"),
    body="""\
## The difference between a script and an automation

A script is run by a person who watches it. An automation runs unattended, on a
schedule, against data nobody inspected first, and its failures are discovered
hours later from a log. That changes every design decision.

Five properties separate the two:

1. **Idempotent** — running it twice does not double the work
2. **Observable** — the log answers *what did it do?* without a re-run
3. **Fail-safe** — a partial failure leaves the system in a valid state
4. **Bounded** — retries, batch sizes and runtimes all have limits
5. **Configurable** — no paths, credentials or thresholds baked into the source

## Idempotency

```python
# Not idempotent: re-running duplicates rows
def import_orders(rows, db):
    for row in rows:
        db.insert(row)

# Idempotent: re-running converges on the same state
def import_orders(rows, db):
    for row in rows:
        db.upsert(row, key="order_id")
```

The test to apply: *if this crashes halfway and I run it again, is the result
correct?* When the answer is no, you have a job that cannot be retried — and it
will eventually need to be.

The file-processing version of the same idea: move the input to `processed/`
only after the output is durably written. Then a crash leaves the input in
place, and the retry does the right thing.

## Logging, not print

```python
import logging

logger = logging.getLogger(__name__)

def process(path):
    logger.info("processing file", extra={"path": str(path)})
    try:
        rows = parse(path)
    except ParseError:
        logger.exception("failed to parse", extra={"path": str(path)})
        raise
    logger.info("processed", extra={"path": str(path), "rows": len(rows)})
```

`print` has no level, no timestamp, no source, and cannot be turned down in
production or up during an incident. `logger.exception` includes the traceback
automatically, and only makes sense inside an `except` block.

The levels have meanings — use them:

| Level | Use for | Who reads it |
| --- | --- | --- |
| DEBUG | internal detail | you, debugging |
| INFO | normal milestones | anyone auditing a run |
| WARNING | recovered, but odd | someone reviewing weekly |
| ERROR | this operation failed | on-call, next morning |
| CRITICAL | the service is down | on-call, now |

Log a **correlation id** on every line of a run. When the 2am job fails, one
grep then reconstructs the whole story.

## Structure: separate the doing from the deciding

```python
def find_input_files(directory: Path) -> list[Path]:      # pure, testable
def transform(rows: list[dict]) -> list[dict]:            # pure, testable
def write_output(rows: list[dict], target: Path) -> None: # I/O, small
def main(argv=None) -> int:                               # wiring + exit code
```

The pure functions get unit tests. `main` gets one integration test. A job
written as a single 200-line function gets neither.

## A CLI people can actually use

```python
import argparse, sys

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import orders from CSV")
    parser.add_argument("source", type=Path, help="input directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would happen, change nothing")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        processed = run(args.source, dry_run=args.dry_run)
    except ImportError_ as exc:
        logger.error("import failed: %s", exc)
        return 1
    logger.info("done", extra={"processed": processed})
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Two details that matter more than they look. **Exit codes**: 0 for success,
non-zero for failure — that is how cron, CI and orchestrators know something
went wrong. **`--dry-run`**: the first thing anyone wants before pointing a new
job at production data.

`main(argv=None)` taking arguments makes the whole CLI testable:
`assert main(["data/", "--dry-run"]) == 0`.

## Configuration and secrets

```python
import os

DATABASE_URL = os.environ["DATABASE_URL"]           # required: fail loudly at startup
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))    # optional: sensible default
```

Use `os.environ[...]` for anything required. Failing at startup with
"KeyError: DATABASE_URL" is far better than failing at 2:47am halfway through a
batch.

Never commit a secret. Never log one. Assume anything printed is retained
somewhere for seven years.

## Failure handling for batches

```python
succeeded, failed = [], []
for record in records:
    try:
        process(record)
        succeeded.append(record.id)
    except RecoverableError:
        logger.warning("skipping record", extra={"id": record.id}, exc_info=True)
        failed.append(record.id)

logger.info("batch complete", extra={"ok": len(succeeded), "failed": len(failed)})
if failed:
    return 2      # partial success: distinguishable from both success and total failure
```

One bad record should not lose the other 50,000 — but the failures must be
counted, logged and reflected in the exit code. Silent skipping is how data goes
missing for a quarter before anyone notices.
""",
    sections={
        "what_is_it": "Automation is software that performs a repeated operational task "
        "without a human driving it: scheduled jobs, file processors, integrations, report "
        "generators.",
        "why_it_exists": "Manual repetition is slow, expensive and inconsistent. Automation "
        "converts a task someone has to remember into a task that simply happens.",
        "how_it_works": "A scheduler (cron, systemd timer, Airflow, an orchestrator) invokes "
        "a process with configuration from the environment. The process does its work, writes "
        "logs, and exits with a status code the scheduler interprets.",
        "when_to_use": "Any task that is repetitive, rule-based, high-volume or "
        "error-prone by hand; anything that must happen on a schedule.",
        "when_not_to_use": "Tasks needing genuine judgement; one-off jobs where automating "
        "costs more than doing it; processes so unstable that the automation would need "
        "rewriting weekly; anything where a wrong action is unrecoverable and there is no "
        "human check.",
        "common_mistakes": "Non-idempotent jobs that cannot be retried; `print` instead of "
        "logging; hardcoded paths and credentials; no exit codes; unbounded retries; deleting "
        "the input before the output is durable; no `--dry-run`; swallowing per-record errors "
        "without counting them.",
        "real_world": "A nightly job pulls yesterday's orders from an API, reconciles them "
        "against the warehouse database, writes an exception report, emails finance and "
        "exits. It has a correlation id per run, alerts on a non-zero exit, and can be "
        "re-run safely for any date.",
        "alternatives": "Orchestrators (Airflow, Prefect, Dagster) when there are "
        "dependencies between jobs; event-driven functions when work is triggered rather "
        "than scheduled; RPA platforms such as UiPath when the target has no API and you must "
        "drive a UI; message queues for high-volume asynchronous work.",
        "performance": "Batch rather than doing per-record I/O; stream large files instead of "
        "loading them; parallelise independent work with a thread pool (I/O-bound) or a "
        "process pool (CPU-bound). Measure first — most 'slow' jobs are slow in one place.",
        "security": "Secrets from the environment or a vault, never from source. Run with "
        "least privilege — a report generator needs SELECT, not DROP. Validate every external "
        "input, including filenames. Never build a shell command by concatenating input: use "
        "`subprocess.run([...])` with a list.",
    },
    starter_code='''\
"""An idempotent file processor, in miniature."""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("processor")


def process_directory(source: Path, *, dry_run: bool = False) -> dict:
    """Process every .txt file, skipping ones already done."""
    source.mkdir(exist_ok=True)
    done = source / "processed"
    done.mkdir(exist_ok=True)

    summary = {"processed": 0, "skipped": 0}
    for path in sorted(source.glob("*.txt")):
        if (done / path.name).exists():
            logger.info("already processed, skipping: %s", path.name)
            summary["skipped"] += 1
            continue
        logger.info("processing %s (%d bytes)", path.name, path.stat().st_size)
        if not dry_run:
            (done / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        summary["processed"] += 1
    return summary


Path("inbox").mkdir(exist_ok=True)
(Path("inbox") / "order-1.txt").write_text("order data", encoding="utf-8")

print(process_directory(Path("inbox")))
print(process_directory(Path("inbox")))   # second run: nothing to do
''',
    examples=(
        Example(
            title="Logging levels beat print",
            code="""\
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger("job")

logger.debug("connection pool size is 5")     # filtered out at INFO
logger.info("starting run")
logger.warning("3 records had missing postcodes; defaulted")
try:
    1 / 0
except ZeroDivisionError:
    logger.exception("record 42 failed")
""",
            output="INFO     starting run\nWARNING  3 records had missing postcodes; defaulted\n"
            "ERROR    record 42 failed\nTraceback (most recent call last):\n  ...\n"
            "ZeroDivisionError: division by zero",
            explanation="The DEBUG line is filtered by configuration, not by editing code. "
            "`logger.exception` adds the traceback with no extra work.",
        ),
        Example(
            title="Exit codes are the interface to the scheduler",
            code="""\
import sys


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: job <source>", file=sys.stderr)
        return 2                      # 2 = usage error, by convention
    print(f"processing {argv[0]}")
    return 0                          # 0 = success


print("no args ->", main([]))
print("with arg ->", main(["data/"]))
""",
            output="usage: job <source>\nno args -> 2\nprocessing data/\nwith arg -> 0",
            explanation="`main(argv=None)` is testable, and the return value becomes the "
            "process exit code via `sys.exit(main())`.",
        ),
    ),
    exercises=(
        ExerciseSpec(
            slug="automation-idempotent-processor",
            title="An idempotent batch processor",
            prompt="""\
Implement `process_batch(records, sink, processed_ids=None)`.

* `records` is a list of dicts, each with an `"id"` and a `"value"`
* `sink.write(record)` persists one record and may raise `RuntimeError`
* skip any record whose id is already in `processed_ids`
* a record that raises must not stop the batch
* return a summary dict: `{"written", "skipped", "failed", "failed_ids"}`
* the ids of successfully written records must be added to `processed_ids`, so
  that a re-run with the same set skips them

This is the shape of every retryable batch job: skip what is done, isolate
failures, report precisely.
""",
            kind=ExerciseKind.CODE,
            level=SkillLevel.PROFESSIONAL,
            difficulty=0.7,
            estimated_minutes=25,
            xp_reward=60,
            starter_files={
                "main.py": '''\
def process_batch(records: list[dict], sink, processed_ids: set | None = None) -> dict:
    """Write each record to `sink`, skipping ones already processed."""
    ...
'''
            },
            hidden_files={
                "test_batch.py": """\
import pytest

from main import process_batch


class Sink:
    def __init__(self, fail_on=()):
        self.written = []
        self.fail_on = set(fail_on)

    def write(self, record):
        if record["id"] in self.fail_on:
            raise RuntimeError(f"cannot write {record['id']}")
        self.written.append(record)


RECORDS = [
    {"id": 1, "value": "a"},
    {"id": 2, "value": "b"},
    {"id": 3, "value": "c"},
]


def test_writes_everything():
    sink = Sink()
    result = process_batch(RECORDS, sink)
    assert result["written"] == 3
    assert result["failed"] == 0
    assert len(sink.written) == 3


def test_skips_already_processed():
    sink = Sink()
    result = process_batch(RECORDS, sink, processed_ids={1, 2})
    assert result["skipped"] == 2
    assert result["written"] == 1


def test_failure_does_not_stop_the_batch():
    sink = Sink(fail_on={2})
    result = process_batch(RECORDS, sink)
    assert result["written"] == 2
    assert result["failed"] == 1
    assert result["failed_ids"] == [2]
    assert len(sink.written) == 2


def test_is_idempotent_across_runs():
    sink = Sink()
    seen = set()
    first = process_batch(RECORDS, sink, processed_ids=seen)
    second = process_batch(RECORDS, sink, processed_ids=seen)
    assert first["written"] == 3
    assert second["written"] == 0
    assert second["skipped"] == 3
    assert len(sink.written) == 3, "a re-run must not duplicate writes"


def test_failed_records_are_retried_on_the_next_run():
    sink = Sink(fail_on={2})
    seen = set()
    process_batch(RECORDS, sink, processed_ids=seen)
    assert 2 not in seen, "a failed record must not be marked as processed"


def test_empty_batch():
    assert process_batch([], Sink())["written"] == 0
"""
            },
            concepts=("automation-design", "exceptions", "logging"),
            hints=(
                HintSpec(
                    "Every record has exactly one of three outcomes: skipped, written, "
                    "or failed. Count each one, and make sure the counts always add up "
                    "to the number of records."
                ),
                HintSpec(
                    "`processed_ids` defaults to None — and it is mutable, so it is "
                    "another mutable-default trap. Create the set inside when none is "
                    "given."
                ),
                HintSpec(
                    "The idempotency test depends on *when* you add the id to "
                    "`processed_ids`. Add it after a successful write, never before — "
                    "otherwise a failed record is marked done and is lost for ever."
                ),
                HintSpec(
                    "```python\nfor record in records:\n"
                    "    if record['id'] in processed_ids:\n        skipped += 1; continue\n"
                    "    try:\n        sink.write(record)\n    except RuntimeError:\n"
                    "        failed_ids.append(record['id']); continue\n"
                    "    processed_ids.add(record['id'])\n    written += 1\n```"
                ),
            ),
            solution_files={
                "main.py": '''\
import logging

logger = logging.getLogger(__name__)


def process_batch(records: list[dict], sink, processed_ids: set | None = None) -> dict:
    """Write each record to ``sink``, skipping ones already processed.

    Designed to be safely re-runnable:

    * a record already in ``processed_ids`` is skipped, so a retry after a crash
      does not duplicate work;
    * an id is recorded *after* a successful write, so a failed record is
      retried rather than silently lost;
    * one failing record does not abort the batch, but every failure is counted
      and returned so the caller can set a non-zero exit code.
    """
    if processed_ids is None:
        processed_ids = set()

    written = 0
    skipped = 0
    failed_ids: list = []

    for record in records:
        record_id = record["id"]
        if record_id in processed_ids:
            logger.debug("skipping already-processed record %s", record_id)
            skipped += 1
            continue
        try:
            sink.write(record)
        except RuntimeError:
            logger.warning("record %s failed and will be retried", record_id, exc_info=True)
            failed_ids.append(record_id)
            continue
        processed_ids.add(record_id)
        written += 1

    logger.info(
        "batch complete: written=%d skipped=%d failed=%d", written, skipped, len(failed_ids)
    )
    return {
        "written": written,
        "skipped": skipped,
        "failed": len(failed_ids),
        "failed_ids": failed_ids,
    }
'''
            },
            solution_explanation="The load-bearing line is `processed_ids.add(record_id)` "
            "*after* the write, not before. Mark-then-write means a crash between the two "
            "loses the record permanently — the next run skips it because it is marked, and "
            "nobody ever finds out. Write-then-mark means a crash causes at worst a duplicate "
            "attempt, which an idempotent sink absorbs. Given the choice between losing data "
            "and repeating work, always choose repeating work.",
            misconception_rules=(
                {
                    "pattern": "must not be marked as processed",
                    "misconception": "mark-before-commit",
                },
                {"pattern": "must not duplicate writes", "misconception": "non-idempotent"},
            ),
        ),
    ),
)

PROFESSIONAL_MODULE = ModuleSpec(
    slug="professional-python",
    title="Professional Python: Objects, Data, Services and Operations",
    summary="Everything between 'my code works' and 'my code runs in production': classes, "
    "files and formats, HTTP clients, tests, and automation that survives being unattended.",
    level=SkillLevel.PROFESSIONAL,
    lessons=(OOP, FILE_HANDLING, APIS, TESTING, AUTOMATION),
)
