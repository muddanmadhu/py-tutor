"""The searchable Python reference.

Each entry answers what a learner actually needs at the moment they look
something up: the signature, what the parameters mean, what it returns, a
runnable example, the mistake people make with it, and what to use instead.

This is the seed set. The schema is designed so that hundreds more can be added
without touching any code — see ``docs/CURRICULUM.md``.
"""

from __future__ import annotations

from app.content.schema import ReferenceSpec

REFERENCE: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        key="print",
        title="print()",
        kind="function",
        module="builtins",
        signature="print(*objects, sep=' ', end='\\n', file=sys.stdout, flush=False)",
        summary="Write objects to a text stream, separated by `sep` and followed by `end`.",
        description="Converts each argument with `str()` and writes the result. Returns None "
        "— it is called for its side effect, so it can never be part of an expression that "
        "needs a value.",
        parameters=(
            {
                "name": "*objects",
                "type": "Any",
                "required": False,
                "description": "Values to write; each is converted with str().",
            },
            {
                "name": "sep",
                "type": "str",
                "required": False,
                "default": "' '",
                "description": "Inserted between values.",
            },
            {
                "name": "end",
                "type": "str",
                "required": False,
                "default": "'\\n'",
                "description": "Appended after the last value.",
            },
            {
                "name": "file",
                "type": "TextIO",
                "required": False,
                "default": "sys.stdout",
                "description": "Destination stream; use sys.stderr for error output.",
            },
            {
                "name": "flush",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Force the stream to flush immediately.",
            },
        ),
        returns="None",
        examples=(
            {
                "title": "Separator and terminator",
                "code": "print('a', 'b', 'c', sep='-', end='!\\n')",
                "output": "a-b-c!",
            },
            {
                "title": "Writing to stderr",
                "code": "import sys\\nprint('something failed', file=sys.stderr)",
                "output": "something failed",
            },
        ),
        real_world_usage="Fine for scripts and debugging. In anything that runs unattended, "
        "use the `logging` module instead: print has no level, no timestamp and cannot be "
        "turned down in production.",
        common_mistakes=(
            {
                "mistake": "`x = print('hi')`",
                "fix": "print returns None. It writes; it does not produce a value.",
            },
            {
                "mistake": "Using print for application logging",
                "fix": "Use logging — you get levels, timestamps, and runtime configuration.",
            },
        ),
        performance_notes="Each call may flush, which is a syscall. Printing inside a tight "
        "loop can dominate runtime; build the output and print once.",
        security_notes="Never print secrets. Standard output is frequently captured and "
        "retained by CI systems, container runtimes and log aggregators.",
        related=("input", "logging.getLogger", "sys.stdout"),
        keywords=("output", "console", "stdout", "display", "write"),
        lesson_slugs=("python-fundamentals",),
    ),
    ReferenceSpec(
        key="input",
        title="input()",
        kind="function",
        module="builtins",
        signature="input(prompt='') -> str",
        summary="Read one line from standard input and return it as a string, without the "
        "trailing newline.",
        description="**Always returns a str**, even when the user types digits. This is the "
        "single most common source of TypeError for beginners.",
        parameters=(
            {
                "name": "prompt",
                "type": "str",
                "required": False,
                "description": "Written to stdout before reading.",
            },
        ),
        returns="str — the line entered, newline stripped.",
        raises=({"type": "EOFError", "when": "Input ends (Ctrl-D, or a closed pipe)."},),
        examples=(
            {
                "title": "Read and convert",
                "code": "age = int(input('Age: '))\\nprint(age + 1)",
                "output": "Age: 30\\n31",
            },
            {
                "title": "Convert defensively",
                "code": "raw = input('Age: ')\\ntry:\\n    age = int(raw)\\n"
                "except ValueError:\\n    print(f'{raw!r} is not a number')",
                "output": "Age: thirty\\n'thirty' is not a number",
            },
        ),
        real_world_usage="Interactive scripts only. Automation reads arguments, environment "
        "variables or files — a job that waits for input at 2am simply hangs.",
        common_mistakes=(
            {
                "mistake": "`age = input(...)` then `age + 1`",
                "fix": "TypeError: convert first with int() or float().",
            },
            {
                "mistake": "`int(input())` with no error handling",
                "fix": "Any non-numeric entry crashes the program. Wrap it in try/except.",
            },
        ),
        security_notes="Never pass input to eval() or exec(). Validate length and content "
        "before use.",
        related=("print", "sys.argv", "argparse.ArgumentParser"),
        keywords=("read", "stdin", "prompt", "user input"),
        lesson_slugs=("variables-and-data-types",),
    ),
    ReferenceSpec(
        key="list.append",
        title="list.append()",
        kind="method",
        module="builtins",
        signature="list.append(object) -> None",
        summary="Add a single object to the end of the list, in place.",
        description="Appends one item, whatever it is. Appending a list adds that list as a "
        "single element — use `extend` to add its contents instead.",
        parameters=(
            {
                "name": "object",
                "type": "Any",
                "required": True,
                "description": "The single item to add.",
            },
        ),
        returns="None — the list is modified in place.",
        examples=(
            {
                "title": "append vs extend",
                "code": "a = [1, 2]\\na.append([3, 4])\\nprint(a)\\n"
                "b = [1, 2]\\nb.extend([3, 4])\\nprint(b)",
                "output": "[1, 2, [3, 4]]\\n[1, 2, 3, 4]",
            },
        ),
        real_world_usage="The standard way to build a list in a loop. When the loop only maps "
        "or filters, a comprehension is clearer and faster.",
        common_mistakes=(
            {
                "mistake": "`items = items.append(x)`",
                "fix": "append returns None; you have just replaced your list with None.",
            },
            {
                "mistake": "Using append when you meant extend",
                "fix": "append adds one element; extend adds each element of an iterable.",
            },
        ),
        performance_notes="Amortised O(1). CPython over-allocates, so most appends do not "
        "reallocate. Appending a million items is fine; `insert(0, x)` a million times is "
        "O(n²) — use collections.deque.",
        related=("list.extend", "list.insert", "list.pop"),
        keywords=("add", "push", "grow", "build a list"),
        lesson_slugs=("lists",),
    ),
    ReferenceSpec(
        key="list.sort",
        title="list.sort()",
        kind="method",
        module="builtins",
        signature="list.sort(*, key=None, reverse=False) -> None",
        summary="Sort the list in place. Returns None.",
        description="Uses Timsort: stable, and adaptive to partially-ordered input. "
        "*Stable* means equal elements keep their relative order, which is what makes "
        "multi-pass sorting work.",
        parameters=(
            {
                "name": "key",
                "type": "Callable",
                "required": False,
                "description": "Called once per element; its result is what gets compared.",
            },
            {
                "name": "reverse",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Sort descending.",
            },
        ),
        returns="None — sorted in place. Use sorted() for a new list.",
        examples=(
            {
                "title": "Sort by a computed key",
                "code": "words = ['banana', 'fig', 'apple']\\nwords.sort(key=len)\\nprint(words)",
                "output": "['fig', 'apple', 'banana']",
            },
            {
                "title": "Two keys, opposite directions",
                "code": "people = [{'n': 'B', 'a': 30}, {'n': 'A', 'a': 30}]\\n"
                "people.sort(key=lambda p: (-p['a'], p['n']))\\n"
                "print([p['n'] for p in people])",
                "output": "['A', 'B']",
            },
        ),
        real_world_usage="Ranking, leaderboards, report ordering. Negate a numeric key to "
        "sort it descending while another key stays ascending — `reverse=True` would flip "
        "both.",
        common_mistakes=(
            {
                "mistake": "`sorted_list = my_list.sort()`",
                "fix": "That assigns None. Use `sorted(my_list)`.",
            },
            {
                "mistake": "Sorting a caller's list in place",
                "fix": "Surprising side effect. Use sorted() unless mutation is the point.",
            },
        ),
        performance_notes="O(n log n) worst case, O(n) on already-sorted input. `key` is "
        "computed once per element (the decorate-sort-undecorate pattern), so an expensive "
        "key function costs n calls, not n log n.",
        related=("sorted", "list.reverse", "operator.itemgetter"),
        keywords=("order", "rank", "arrange", "sort by"),
        lesson_slugs=("lists",),
    ),
    ReferenceSpec(
        key="dict.get",
        title="dict.get()",
        kind="method",
        module="builtins",
        signature="dict.get(key, default=None) -> Any",
        summary="Return the value for `key`, or `default` when the key is absent — without "
        "raising.",
        description="The safe alternative to `d[key]`. Choose deliberately: `d[key]` asserts "
        "the key must be present, and its KeyError is a useful bug report. `.get` says "
        "absence is expected.",
        parameters=(
            {"name": "key", "type": "Hashable", "required": True, "description": "Key to look up."},
            {
                "name": "default",
                "type": "Any",
                "required": False,
                "default": "None",
                "description": "Returned when the key is missing.",
            },
        ),
        returns="The value, or `default`.",
        examples=(
            {
                "title": "Fallback value",
                "code": "config = {'host': 'localhost'}\\nprint(config.get('port', 8000))",
                "output": "8000",
            },
            {
                "title": "The counting idiom",
                "code": "counts = {}\\nfor c in 'aabbc':\\n    counts[c] = counts.get(c, 0) + 1\\n"
                "print(counts)",
                "output": "{'a': 2, 'b': 2, 'c': 1}",
            },
        ),
        real_world_usage="Reading optional fields from parsed JSON, applying configuration "
        "defaults, counting.",
        common_mistakes=(
            {
                "mistake": "`d.get(key, [])` then appending to the result",
                "fix": "The default is not stored in the dict, so the append is lost. Use "
                "setdefault or defaultdict.",
            },
            {
                "mistake": "Using .get everywhere",
                "fix": "A silent None flowing three layers down is harder to debug than a "
                "KeyError at the source.",
            },
        ),
        performance_notes="O(1) average, marginally slower than `d[key]` because of the "
        "default handling.",
        related=("dict.setdefault", "dict.items", "collections.defaultdict"),
        keywords=("default", "missing key", "safe lookup", "keyerror"),
        lesson_slugs=("dictionaries",),
    ),
    ReferenceSpec(
        key="str.split",
        title="str.split()",
        kind="method",
        module="builtins",
        signature="str.split(sep=None, maxsplit=-1) -> list[str]",
        summary="Split a string into a list of substrings.",
        description="With no separator, splits on runs of any whitespace and discards empty "
        "results — which is almost always what you want for prose. With an explicit "
        "separator, consecutive separators produce empty strings.",
        parameters=(
            {
                "name": "sep",
                "type": "str | None",
                "required": False,
                "default": "None",
                "description": "Delimiter. None means split on any whitespace run.",
            },
            {
                "name": "maxsplit",
                "type": "int",
                "required": False,
                "default": "-1",
                "description": "Maximum number of splits; -1 means no limit.",
            },
        ),
        returns="list[str]",
        examples=(
            {
                "title": "Whitespace vs explicit separator",
                "code": "print('a  b   c'.split())\\nprint('a,,b'.split(','))",
                "output": "['a', 'b', 'c']\\n['a', '', 'b']",
            },
            {
                "title": "Limiting the splits",
                "code": "print('key=value=extra'.split('=', maxsplit=1))",
                "output": "['key', 'value=extra']",
            },
        ),
        real_world_usage="Parsing log lines, splitting `KEY=VALUE` pairs (always with "
        "maxsplit=1), tokenising text.",
        common_mistakes=(
            {
                "mistake": "`line.split(',')` to parse CSV",
                "fix": "Breaks on any quoted field containing a comma. Use the csv module.",
            },
            {
                "mistake": "Expecting `'a  b'.split(' ')` to give two items",
                "fix": "It gives `['a', '', 'b']`. Omit the separator to collapse whitespace.",
            },
        ),
        performance_notes="Linear in the length of the string. For a single split, "
        "`partition()` is faster and returns a fixed-size tuple.",
        related=("str.join", "str.strip", "str.partition", "re.split"),
        keywords=("parse", "tokenize", "separate", "delimiter"),
        lesson_slugs=("dictionaries",),
    ),
    ReferenceSpec(
        key="enumerate",
        title="enumerate()",
        kind="function",
        module="builtins",
        signature="enumerate(iterable, start=0) -> Iterator[tuple[int, Any]]",
        summary="Yield `(index, item)` pairs while iterating.",
        description="Replaces the manual counter and the `range(len(...))` anti-pattern. "
        "Lazy: it does not build a list.",
        parameters=(
            {
                "name": "iterable",
                "type": "Iterable",
                "required": True,
                "description": "Any iterable.",
            },
            {
                "name": "start",
                "type": "int",
                "required": False,
                "default": "0",
                "description": "First index value — use 1 for human-facing numbering.",
            },
        ),
        returns="An iterator of (index, item) tuples.",
        examples=(
            {
                "title": "Human numbering",
                "code": "for i, task in enumerate(['write', 'test'], start=1):\\n"
                "    print(f'{i}. {task}')",
                "output": "1. write\\n2. test",
            },
        ),
        real_world_usage="Numbered output, reporting the line number of a bad record while "
        "parsing a file, progress reporting.",
        common_mistakes=(
            {
                "mistake": "`for i in range(len(items))` then `items[i]`",
                "fix": "Iterate directly, or use enumerate when you need the index too.",
            },
            {
                "mistake": "Forgetting `start=1` and printing a task list from 0",
                "fix": "enumerate(items, start=1).",
            },
        ),
        performance_notes="Constant memory — it is a lazy iterator, not a list.",
        related=("zip", "range", "itertools.count"),
        keywords=("index", "counter", "position", "loop with index"),
        lesson_slugs=("loops",),
    ),
    ReferenceSpec(
        key="zip",
        title="zip()",
        kind="function",
        module="builtins",
        signature="zip(*iterables, strict=False) -> Iterator[tuple]",
        summary="Iterate several sequences in parallel, yielding tuples.",
        description="Stops at the shortest input — silently, unless `strict=True` "
        "(Python 3.10+), which raises on a length mismatch.",
        parameters=(
            {
                "name": "*iterables",
                "type": "Iterable",
                "required": True,
                "description": "Two or more iterables.",
            },
            {
                "name": "strict",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Raise ValueError if the lengths differ.",
            },
        ),
        returns="An iterator of tuples.",
        examples=(
            {
                "title": "Pairing two lists",
                "code": "for name, score in zip(['a', 'b'], [90, 80]):\\n    print(name, score)",
                "output": "a 90\\nb 80",
            },
            {
                "title": "Building a dict",
                "code": "print(dict(zip(['x', 'y'], [1, 2])))",
                "output": "{'x': 1, 'y': 2}",
            },
            {
                "title": "Catching a mismatch",
                "code": "list(zip([1, 2, 3], [1, 2], strict=True))",
                "output": "ValueError: zip() argument 2 is shorter than argument 1",
            },
        ),
        real_world_usage="Pairing headers with values, combining parallel result sets, "
        "transposing rows and columns with `zip(*rows)`.",
        common_mistakes=(
            {
                "mistake": "Not noticing silent truncation",
                "fix": "Pass strict=True when the lengths are supposed to match.",
            },
            {
                "mistake": "Reusing a zip object",
                "fix": "It is an iterator: once consumed it is empty. Wrap in list() to reuse.",
            },
        ),
        performance_notes="Lazy and constant-memory.",
        related=("enumerate", "itertools.zip_longest", "dict"),
        keywords=("pair", "parallel", "combine", "transpose"),
        lesson_slugs=("loops",),
    ),
    ReferenceSpec(
        key="open",
        title="open()",
        kind="function",
        module="builtins",
        signature="open(file, mode='r', encoding=None, newline=None, ...) -> IO",
        summary="Open a file and return a file object. Always use it with `with`.",
        description="Text mode decodes bytes using `encoding`; binary mode ('b') does not. "
        "Always pass `encoding='utf-8'` explicitly — the default depends on the platform "
        "locale, so the same code can behave differently in a container.",
        parameters=(
            {"name": "file", "type": "str | Path", "required": True, "description": "Path."},
            {
                "name": "mode",
                "type": "str",
                "required": False,
                "default": "'r'",
                "description": "r read, w truncate-write, a append, x exclusive create, b binary.",
            },
            {
                "name": "encoding",
                "type": "str",
                "required": False,
                "description": "Text encoding. Always pass 'utf-8' explicitly.",
            },
            {
                "name": "newline",
                "type": "str",
                "required": False,
                "description": "Pass '' when reading or writing CSV.",
            },
        ),
        returns="A file object (a context manager).",
        raises=(
            {"type": "FileNotFoundError", "when": "Mode 'r' and the file does not exist."},
            {"type": "PermissionError", "when": "The process may not access the path."},
            {"type": "FileExistsError", "when": "Mode 'x' and the file already exists."},
        ),
        examples=(
            {
                "title": "Read safely",
                "code": "with open('data.txt', encoding='utf-8') as f:\\n    text = f.read()",
                "output": "",
            },
            {
                "title": "Stream a large file",
                "code": "with open('huge.log', encoding='utf-8') as f:\\n"
                "    for line in f:\\n        process(line)",
                "output": "",
            },
        ),
        real_world_usage="`pathlib.Path.read_text()` / `write_text()` are cleaner for whole "
        "small files. Use open() when you need to stream, append, or work in binary.",
        common_mistakes=(
            {
                "mistake": "Not using `with`",
                "fix": "An exception then leaks the handle and can lose buffered writes.",
            },
            {
                "mistake": "Opening with 'w' to inspect a file",
                "fix": "'w' truncates on open, before you write anything. Use 'r'.",
            },
            {
                "mistake": "`f.read()` on a multi-gigabyte file",
                "fix": "Iterate the handle to stream it line by line.",
            },
        ),
        performance_notes="Buffered by default. Reading line by line is constant memory; "
        "`read()` is O(file size) in RAM.",
        security_notes="Never open a path built from unvalidated user input — `../` escapes "
        "any prefix. Resolve the path and verify it is inside the intended directory with "
        "`Path.is_relative_to`.",
        related=("pathlib.Path", "csv.DictReader", "json.load"),
        keywords=("file", "read", "write", "io", "encoding"),
        lesson_slugs=("file-handling",),
    ),
    ReferenceSpec(
        key="pathlib.Path",
        title="pathlib.Path",
        kind="class",
        module="pathlib",
        signature="Path(*segments)",
        summary="An object-oriented filesystem path that works the same on every platform.",
        description="Replaces os.path string juggling. The `/` operator joins segments with "
        "the correct separator; the methods do what their names say.",
        parameters=(
            {
                "name": "*segments",
                "type": "str | Path",
                "required": False,
                "description": "Path components, joined with the platform separator.",
            },
        ),
        returns="A Path instance (PosixPath or WindowsPath).",
        examples=(
            {
                "title": "Build and inspect",
                "code": "from pathlib import Path\\np = Path('data') / 'reports' / 'q3.csv'\\n"
                "print(p, p.suffix, p.stem, p.parent)",
                "output": "data/reports/q3.csv .csv q3 data/reports",
            },
            {
                "title": "Create, write, read",
                "code": "p.parent.mkdir(parents=True, exist_ok=True)\\n"
                "p.write_text('a,b\\\\n', encoding='utf-8')\\n"
                "print(p.read_text(encoding='utf-8'))",
                "output": "a,b",
            },
            {
                "title": "Find files recursively",
                "code": "for csv in Path('data').rglob('*.csv'):\\n    print(csv)",
                "output": "data/reports/q3.csv",
            },
        ),
        real_world_usage="The default for any filesystem work in modern Python. "
        "`Path.replace()` is an atomic rename on POSIX — write to a temp file and replace, "
        "so readers never see a half-written file.",
        common_mistakes=(
            {
                "mistake": "Building paths with string concatenation",
                "fix": "Breaks on Windows and on trailing separators. Use `/`.",
            },
            {
                "mistake": "`Path.exists()` then open",
                "fix": "A race condition. Just open it and handle FileNotFoundError.",
            },
        ),
        performance_notes="Each stat-based method (`exists`, `is_file`, `stat`) is a syscall. "
        "In a loop over thousands of files, call `stat()` once and reuse the result.",
        security_notes="`base / user_input` does not prevent traversal. Always "
        "`(base / candidate).resolve().is_relative_to(base.resolve())`.",
        related=("open", "os.path", "shutil.move"),
        keywords=("path", "directory", "filesystem", "glob", "traversal"),
        lesson_slugs=("file-handling",),
    ),
    ReferenceSpec(
        key="json.loads",
        title="json.loads()",
        kind="function",
        module="json",
        signature="json.loads(s, *, cls=None, object_hook=None, parse_float=None, ...) -> Any",
        summary="Parse a JSON string into Python objects.",
        description="`loads` takes a **s**tring; `load` takes a file object. Same for "
        "`dumps`/`dump`. JSON objects become dicts, arrays become lists, null becomes None.",
        parameters=(
            {
                "name": "s",
                "type": "str | bytes",
                "required": True,
                "description": "The JSON document.",
            },
            {
                "name": "object_hook",
                "type": "Callable",
                "required": False,
                "description": "Called on every decoded object; use it to build custom types.",
            },
            {
                "name": "parse_float",
                "type": "Callable",
                "required": False,
                "description": "Use `decimal.Decimal` here for money.",
            },
        ),
        returns="dict, list, str, int, float, bool or None.",
        raises=(
            {
                "type": "json.JSONDecodeError",
                "when": "The text is not valid JSON. Carries .lineno, .colno and .pos.",
            },
        ),
        examples=(
            {
                "title": "Parse and handle failure",
                "code": "import json\\ntry:\\n    data = json.loads('{bad}')\\n"
                "except json.JSONDecodeError as exc:\\n"
                "    print(f'invalid at line {exc.lineno}, column {exc.colno}')",
                "output": "invalid at line 1, column 2",
            },
            {
                "title": "Money without float drift",
                "code": "from decimal import Decimal\\nimport json\\n"
                "print(json.loads('{\\\"amount\\\": 19.99}', parse_float=Decimal))",
                "output": "{'amount': Decimal('19.99')}",
            },
        ),
        real_world_usage="Every API response. Always wrap it: a proxy returning an HTML error "
        "page is the classic cause of a JSONDecodeError in production.",
        common_mistakes=(
            {
                "mistake": "Confusing loads/load and dumps/dump",
                "fix": "The 's' is for string. No 's' means a file object.",
            },
            {
                "mistake": "Expecting datetimes or tuples to survive a round trip",
                "fix": "JSON has neither. Datetimes go in as ISO strings and come back as "
                "strings; tuples come back as lists.",
            },
            {"mistake": "Parsing money as float", "fix": "Pass parse_float=Decimal."},
        ),
        performance_notes="The C implementation is used automatically. For very large "
        "payloads, `orjson` is several times faster; for huge documents, stream with "
        "`ijson` rather than loading the whole thing.",
        security_notes="Safe against code execution (unlike pickle), but not against "
        "resource exhaustion: bound the size of anything you parse from a network source, "
        "and beware deeply nested documents.",
        related=("json.dumps", "json.load", "csv.DictReader"),
        keywords=("json", "parse", "decode", "api response"),
        lesson_slugs=("file-handling", "apis-and-http"),
    ),
    ReferenceSpec(
        key="csv.DictReader",
        title="csv.DictReader",
        kind="class",
        module="csv",
        signature="csv.DictReader(f, fieldnames=None, restkey=None, restval=None, "
        "dialect='excel', ...)",
        summary="Iterate a CSV file as dicts keyed by the header row.",
        description="Handles quoting, embedded commas, embedded newlines and escaping — all "
        "the things that make `line.split(',')` wrong.",
        parameters=(
            {
                "name": "f",
                "type": "TextIO",
                "required": True,
                "description": "An open file object. Open it with newline=''.",
            },
            {
                "name": "fieldnames",
                "type": "Sequence[str]",
                "required": False,
                "description": "Use when the file has no header row.",
            },
            {
                "name": "restval",
                "type": "Any",
                "required": False,
                "description": "Value for keys missing from a short row.",
            },
        ),
        returns="An iterator of dicts. **Every value is a string.**",
        examples=(
            {
                "title": "Read and convert at the boundary",
                "code": "import csv\\nwith open('s.csv', newline='', encoding='utf-8') as f:\\n"
                "    total = sum(float(row['amount']) for row in csv.DictReader(f))",
                "output": "",
            },
        ),
        real_world_usage="Supplier feeds, exports, report inputs. Convert types once, on the "
        "way in, rather than at every point of use.",
        common_mistakes=(
            {
                "mistake": "Omitting newline=''",
                "fix": "Produces blank rows between records on Windows.",
            },
            {
                "mistake": "Treating values as numbers",
                "fix": "They are strings. `row['amount'] + row['tax']` concatenates.",
            },
            {
                "mistake": "Parsing CSV with split(',')",
                "fix": "One quoted field with a comma breaks it. Real CSV is full of them.",
            },
        ),
        performance_notes="C-accelerated and streams row by row, so memory is constant. For "
        "millions of rows with heavy analysis, Polars or PyArrow are far faster.",
        security_notes="Beware CSV injection: a value beginning with `=`, `+`, `-` or `@` is "
        "executed as a formula when opened in a spreadsheet. Prefix untrusted values with an "
        "apostrophe when exporting.",
        related=("csv.DictWriter", "open", "json.loads"),
        keywords=("csv", "spreadsheet", "import", "tabular"),
        lesson_slugs=("file-handling",),
    ),
    ReferenceSpec(
        key="requests.get",
        title="requests.get()",
        kind="function",
        module="requests",
        signature="requests.get(url, params=None, headers=None, timeout=None, **kwargs) "
        "-> Response",
        summary="Send an HTTP GET request. Always pass a timeout.",
        description="`requests` is not in the standard library, and it is not available in "
        "this sandbox — the lesson exercises use a stub client with the same shape. The API "
        "is worth knowing because it is what you will use in real work.",
        parameters=(
            {"name": "url", "type": "str", "required": True, "description": "Target URL."},
            {
                "name": "params",
                "type": "dict",
                "required": False,
                "description": "Query parameters; correctly URL-encoded for you.",
            },
            {
                "name": "headers",
                "type": "dict",
                "required": False,
                "description": "Request headers, e.g. Authorization.",
            },
            {
                "name": "timeout",
                "type": "float | tuple",
                "required": False,
                "description": "Seconds, or (connect, read). **Omitting it means wait for ever.**",
            },
        ),
        returns="A Response with .status_code, .json(), .text, .headers and .raise_for_status().",
        raises=(
            {"type": "requests.Timeout", "when": "The timeout elapsed."},
            {"type": "requests.ConnectionError", "when": "DNS, refused connection, TLS."},
            {"type": "requests.HTTPError", "when": "raise_for_status() on a 4xx/5xx."},
        ),
        examples=(
            {
                "title": "A correct call",
                "code": "r = requests.get(url, headers={'Authorization': f'Bearer {t}'},\\n"
                "                 timeout=10)\\nr.raise_for_status()\\ndata = r.json()",
                "output": "",
            },
            {
                "title": "Reuse the connection",
                "code": "with requests.Session() as s:\\n    s.headers['Authorization'] = ...\\n"
                "    for page in range(10):\\n        s.get(url, params={'page': page},\\n"
                "                                          timeout=10)",
                "output": "",
            },
        ),
        real_world_usage="A Session reuses the TCP/TLS connection, which is often a 3–5× "
        "speedup over repeated `requests.get` for paginated APIs.",
        common_mistakes=(
            {
                "mistake": "No timeout",
                "fix": "The default is to wait for ever. One hung server takes a worker with it.",
            },
            {
                "mistake": "Not checking the status",
                "fix": "A 404 body is still a body. Call raise_for_status() or check explicitly.",
            },
            {
                "mistake": "verify=False to silence a TLS error",
                "fix": "That disables certificate checking entirely. Fix the trust store.",
            },
        ),
        performance_notes="Use a Session for connection pooling. Parallelise independent "
        "calls with a ThreadPoolExecutor (the work is I/O-bound, so the GIL is not a "
        "constraint) or use httpx with asyncio.",
        security_notes="Always HTTPS. Never log the Authorization header. Never fetch a "
        "user-supplied URL without an allowlist — that is server-side request forgery.",
        related=("json.loads", "urllib.request.urlopen"),
        keywords=("http", "api", "rest", "get", "timeout", "retry"),
        lesson_slugs=("apis-and-http",),
    ),
    ReferenceSpec(
        key="pytest.raises",
        title="pytest.raises()",
        kind="function",
        module="pytest",
        signature="pytest.raises(expected_exception, *, match=None)",
        summary="Assert that a block raises the exception you expect.",
        description="A context manager. The test fails if the block does not raise, or "
        "raises something else. `match` additionally checks the message against a regex.",
        parameters=(
            {
                "name": "expected_exception",
                "type": "type[Exception] | tuple",
                "required": True,
                "description": "The exception class (or a tuple of classes) expected.",
            },
            {
                "name": "match",
                "type": "str",
                "required": False,
                "description": "Regex the string form of the exception must contain.",
            },
        ),
        returns="An ExceptionInfo; `.value` is the exception instance.",
        examples=(
            {
                "title": "Assert the type and the message",
                "code": "with pytest.raises(ValueError, match='must be positive'):\\n"
                "    withdraw(-5)",
                "output": "",
            },
            {
                "title": "Inspect the exception",
                "code": "with pytest.raises(ConfigError) as info:\\n    load({}, 'host')\\n"
                "assert 'host' in str(info.value)\\n"
                "assert isinstance(info.value.__cause__, KeyError)",
                "output": "",
            },
        ),
        real_world_usage="Every validation path deserves one. An error path with no test is "
        "an error path that has never run.",
        common_mistakes=(
            {
                "mistake": "`pytest.raises(Exception)`",
                "fix": "Passes for any failure at all, including a typo in your test. Name the "
                "specific class.",
            },
            {
                "mistake": "Putting several calls inside one raises block",
                "fix": "The first one to raise satisfies it; the rest never run.",
            },
        ),
        related=("pytest.fixture", "unittest.mock.patch"),
        keywords=("test", "exception", "assert raises", "error path"),
        lesson_slugs=("testing",),
    ),
    ReferenceSpec(
        key="logging.getLogger",
        title="logging.getLogger()",
        kind="function",
        module="logging",
        signature="logging.getLogger(name=None) -> Logger",
        summary="Return the logger with the given name, creating it if needed.",
        description="Loggers are singletons per name, so `getLogger(__name__)` at module "
        "level is the standard idiom: the log line then identifies its source, and the "
        "hierarchy lets you configure whole subsystems at once.",
        parameters=(
            {
                "name": "name",
                "type": "str",
                "required": False,
                "description": "Dotted name; conventionally __name__. None returns the root.",
            },
        ),
        returns="A Logger with .debug/.info/.warning/.error/.critical/.exception.",
        examples=(
            {
                "title": "Module-level logger",
                "code": "import logging\\nlogger = logging.getLogger(__name__)\\n"
                "logger.info('processing %s', filename)",
                "output": "",
            },
            {
                "title": "Log an exception with its traceback",
                "code": "try:\\n    risky()\\nexcept ValueError:\\n"
                "    logger.exception('risky() failed')\\n    raise",
                "output": "",
            },
        ),
        real_world_usage="Configure once at the entry point with `basicConfig` or "
        "`dictConfig`; never configure logging inside a library module. Use structured "
        "fields (`extra={...}`) so logs can be queried rather than grepped.",
        common_mistakes=(
            {
                "mistake": "print() instead of logging",
                "fix": "No level, no timestamp, no runtime control.",
            },
            {
                "mistake": "f-strings in log calls: `logger.info(f'x is {x}')`",
                "fix": "Use `logger.info('x is %s', x)` — formatting is then skipped entirely "
                "when the level is disabled.",
            },
            {
                "mistake": "logger.error() inside an except block",
                "fix": "logger.exception() adds the traceback, which is the useful part.",
            },
        ),
        performance_notes="A disabled level costs a single comparison — provided you use "
        "%-style lazy formatting rather than building the string yourself.",
        security_notes="Never log credentials, tokens, full request bodies or personal data. "
        "Logs are retained, shipped to third parties and read by people who do not have "
        "access to the database.",
        related=("logging.basicConfig", "print"),
        keywords=("log", "logging", "observability", "debug", "audit"),
        lesson_slugs=("automation",),
    ),
    ReferenceSpec(
        key="dataclasses.dataclass",
        title="@dataclass",
        kind="decorator",
        module="dataclasses",
        signature="@dataclass(*, init=True, repr=True, eq=True, order=False, frozen=False, "
        "slots=False, kw_only=False)",
        summary="Generate __init__, __repr__ and __eq__ from annotated class attributes.",
        description="Removes the boilerplate from value objects. `frozen=True` makes "
        "instances immutable and hashable; `slots=True` removes the per-instance dict, "
        "cutting memory and speeding up attribute access.",
        parameters=(
            {
                "name": "frozen",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Immutable and hashable. The right default for value objects.",
            },
            {
                "name": "slots",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Use __slots__: less memory, faster attribute access.",
            },
            {
                "name": "order",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "Also generate __lt__, __le__, __gt__, __ge__.",
            },
            {
                "name": "kw_only",
                "type": "bool",
                "required": False,
                "default": "False",
                "description": "All fields become keyword-only — good for wide records.",
            },
        ),
        returns="The decorated class, with the generated methods added.",
        examples=(
            {
                "title": "An immutable value object",
                "code": "from dataclasses import dataclass\\n\\n"
                "@dataclass(frozen=True, slots=True)\\nclass Point:\\n"
                "    x: float\\n    y: float\\n\\n"
                "print(Point(1, 2))\\nprint(Point(1, 2) == Point(1, 2))",
                "output": "Point(x=1, y=2)\\nTrue",
            },
            {
                "title": "Mutable defaults need a factory",
                "code": "from dataclasses import dataclass, field\\n\\n@dataclass\\n"
                "class Basket:\\n    items: list[str] = field(default_factory=list)",
                "output": "",
            },
        ),
        real_world_usage="Configuration objects, DTOs, domain value types, anything parsed "
        "from JSON. Use Pydantic instead when you need validation and coercion at a trust "
        "boundary.",
        common_mistakes=(
            {
                "mistake": "`items: list = []`",
                "fix": "Raises ValueError — dataclasses catch the mutable-default bug for you. "
                "Use field(default_factory=list).",
            },
            {
                "mistake": "Forgetting the type annotation",
                "fix": "A bare `x = 0` is a class attribute, not a field. It will not appear in "
                "__init__.",
            },
        ),
        performance_notes="`slots=True` typically cuts instance memory by around 30% and "
        "speeds up attribute access. For millions of records, a NamedTuple is smaller still.",
        related=("typing.NamedTuple", "property", "enum.Enum"),
        keywords=("dataclass", "value object", "dto", "record", "immutable"),
        lesson_slugs=("object-oriented-programming",),
    ),
)
