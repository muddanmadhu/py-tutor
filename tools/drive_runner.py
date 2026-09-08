"""Drive runner/entrypoint.py on a developer machine, outside a container.

The supervisor hardcodes /workspace because that is the tmpfs the container
mounts. This harness points it at a temporary directory instead so the protocol
and the safety guards can be exercised on a laptop.

    python3 tools/drive_runner.py

It is a demonstration/diagnostic tool, not part of the deployed system: in
production the supervisor is the container entrypoint and reads its job from
stdin.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_supervisor(workspace: Path):
    """Import runner/entrypoint.py and redirect its workspace."""
    spec = importlib.util.spec_from_file_location(
        "pyforge_runner_entrypoint", ROOT / "runner" / "entrypoint.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.WORKSPACE = workspace
    return module


SCENARIOS: list[tuple[str, dict, str]] = [
    (
        "1. a normal program produces output",
        {
            "mode": "script",
            "entrypoint": "main.py",
            "files": {"main.py": "print('hello from the sandbox', 6 * 7)"},
            "timeout_seconds": 5,
        },
        "expect ok=True, stdout contains 42",
    ),
    (
        "2. multiple files are importable",
        {
            "mode": "script",
            "entrypoint": "main.py",
            "files": {
                "main.py": "from helper import shout\nprint(shout('multi-file works'))",
                "helper.py": "def shout(text):\n    return text.upper() + '!'",
            },
            "timeout_seconds": 5,
        },
        "expect ok=True, stdout is upper-cased",
    ),
    (
        "3. stdin is delivered to the program",
        {
            "mode": "script",
            "entrypoint": "main.py",
            "files": {"main.py": "print(input().upper())"},
            "stdin": "quiet\n",
            "timeout_seconds": 5,
        },
        "expect stdout == QUIET",
    ),
    (
        "4. a traceback is captured, not swallowed",
        {
            "mode": "script",
            "entrypoint": "main.py",
            "files": {"main.py": "print(undefined_name)"},
            "timeout_seconds": 5,
        },
        "expect ok=False, stderr contains NameError",
    ),
    (
        "5. an infinite loop is killed at the time limit",
        {
            "mode": "script",
            "entrypoint": "main.py",
            "files": {"main.py": "while True:\n    pass"},
            "timeout_seconds": 2,
        },
        "expect timed_out=True and a learner-facing explanation",
    ),
    (
        "6. runaway output is truncated",
        {
            "mode": "script",
            "entrypoint": "main.py",
            "files": {"main.py": "print('x' * 400_000)"},
            "timeout_seconds": 10,
            "max_output_bytes": 4096,
        },
        "expect stdout_truncated=True and a bounded payload",
    ),
    (
        "7. a path escape is refused before anything runs",
        {
            "mode": "script",
            "entrypoint": "main.py",
            "files": {"main.py": "pass", "../../../etc/pyforge-probe": "owned"},
            "timeout_seconds": 5,
        },
        "expect a protocol error, no execution",
    ),
    (
        "8. pytest mode grades a hidden suite",
        {
            "mode": "pytest",
            "files": {
                "main.py": "def add(a, b):\n    return a + b\n",
                "test_main.py": (
                    "from main import add\n\n\n"
                    "def test_add():\n    assert add(2, 2) == 4\n\n\n"
                    "def test_add_negative():\n    assert add(-1, 1) == 0\n"
                ),
            },
            "pytest_args": ["-v", "--color=no", "-p", "no:cacheprovider"],
            "timeout_seconds": 30,
        },
        "expect PASSED lines (skipped if pytest is unavailable)",
    ),
]


def main() -> int:
    """Run every scenario and print a compact report."""
    failures = 0
    for title, job, expectation in SCENARIOS:
        with tempfile.TemporaryDirectory(prefix="pyforge-drive-") as tmp:
            workspace = Path(tmp)
            supervisor = load_supervisor(workspace)
            print(f"\n{'=' * 74}\n{title}\n  {expectation}\n{'-' * 74}")
            try:
                result = supervisor.run(job)
            except supervisor.JobError as exc:
                print(f"  REFUSED (protocol error): {exc}")
                continue
            except Exception as exc:  # noqa: BLE001 - diagnostic tool
                print(f"  UNEXPECTED {type(exc).__name__}: {exc}")
                failures += 1
                continue

            print(f"  ok={result['ok']}  exit={result['exit_code']}  "
                  f"timed_out={result['timed_out']}  {result['duration_ms']}ms  "
                  f"truncated={result['stdout_truncated']}")
            if result["stdout"]:
                shown = result["stdout"][:300]
                print(f"  stdout: {shown!r}{' …' if len(result['stdout']) > 300 else ''}")
                print(f"  stdout bytes: {len(result['stdout'])}")
            if result["stderr"]:
                print(f"  stderr: {result['stderr'][:400]!r}")
    return failures


if __name__ == "__main__":
    print("Driving the PyForge sandbox supervisor outside a container")
    print(f"interpreter: {sys.version.split()[0]}")
    code = main()
    print(f"\n{'=' * 74}\nunexpected failures: {code}")
    sys.exit(min(code, 1))
