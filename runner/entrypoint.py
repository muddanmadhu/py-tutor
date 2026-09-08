"""In-container entrypoint for the PyForge sandbox.

Reads a single JSON *job* document from stdin, materialises the learner's files
into the working directory, executes them under additional in-container limits,
and writes a single JSON *result* document to stdout.

The process boundary matters: the child (learner code) writes to pipes owned by
this supervisor, so learner output can never be confused with the result
envelope. Anything the supervisor itself prints is protocol; anything the child
prints is data.

Job schema
----------
```json
{
  "mode":             "script" | "pytest",
  "entrypoint":       "main.py",          // script mode
  "pytest_args":      ["-q", "tests"],    // pytest mode
  "files":            {"main.py": "print('hi')"},
  "stdin":            "",
  "timeout_seconds":  10,
  "max_output_bytes": 65536
}
```

Result schema
-------------
```json
{
  "ok": true, "exit_code": 0, "stdout": "hi\n", "stderr": "",
  "timed_out": false, "duration_ms": 31,
  "stdout_truncated": false, "stderr_truncated": false, "error": null
}
```

This module is intentionally dependency-free and stdlib-only: it must start in
a few milliseconds inside a minimal image.
"""

from __future__ import annotations

import json
import os
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path("/workspace")

# Hard ceilings applied inside the container as defence in depth. The container
# runtime already enforces stricter memory/PID limits; these protect against a
# misconfigured caller and bound pathological single-process behaviour.
MAX_ADDRESS_SPACE_BYTES = 1_024 * 1024 * 1024  # 1 GiB virtual address space
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # any single file the child writes
MAX_PROCESSES = 48
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024
GRACE_PERIOD_SECONDS = 1.0


class JobError(Exception):
    """The job document is malformed or unsafe to execute."""


def _fail(message: str, *, exit_code: int = 2) -> None:
    """Emit a protocol-level failure and exit."""
    _emit(
        {
            "ok": False,
            "exit_code": exit_code,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "duration_ms": 0,
            "stdout_truncated": False,
            "stderr_truncated": False,
            "error": message,
        }
    )
    raise SystemExit(0)


def _emit(result: dict) -> None:
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()


def _read_job() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        raise JobError("empty job document")
    try:
        job = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise JobError(f"invalid job JSON: {exc}") from exc
    if not isinstance(job, dict):
        raise JobError("job document must be a JSON object")
    return job


def _safe_relative_path(name: str) -> Path:
    """Resolve ``name`` inside the workspace, rejecting escapes.

    Rejects absolute paths, parent traversal, NUL bytes and anything that
    resolves outside ``/workspace`` (which also covers symlink games, since the
    workspace starts empty and is a tmpfs).
    """
    if not name or "\x00" in name:
        raise JobError(f"invalid file name: {name!r}")
    candidate = Path(name)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise JobError(f"unsafe file path rejected: {name!r}")
    target = (WORKSPACE / candidate).resolve()
    workspace = WORKSPACE.resolve()
    if target != workspace and workspace not in target.parents:
        raise JobError(f"path escapes workspace: {name!r}")
    return target


def _materialise(files: dict) -> None:
    if not isinstance(files, dict) or not files:
        raise JobError("job.files must be a non-empty object")
    for name, content in files.items():
        if not isinstance(name, str) or not isinstance(content, str):
            raise JobError("job.files must map string paths to string contents")
        target = _safe_relative_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _apply_child_limits() -> None:
    """Run in the forked child immediately before ``exec``.

    Each limit is best-effort. The container runtime is the *primary* enforcement
    for memory and process count (cgroups via ``--memory`` and ``--pids-limit``);
    these rlimits are defence in depth for the case where the supervisor is run
    outside a container. Some platforms refuse individual limits — macOS rejects
    ``RLIMIT_AS`` for the interpreter — and a hard failure there would take down
    the whole run rather than degrade one guard.
    """
    # New process group so a timeout kills the whole tree, not just the leader.
    os.setsid()
    for which, value in (
        (resource.RLIMIT_AS, MAX_ADDRESS_SPACE_BYTES),
        (resource.RLIMIT_FSIZE, MAX_FILE_SIZE_BYTES),
        (resource.RLIMIT_NPROC, MAX_PROCESSES),
        (resource.RLIMIT_CORE, 0),
    ):
        try:
            resource.setrlimit(which, (value, value))
        except (ValueError, OSError):
            continue


def _build_command(job: dict) -> list[str]:
    """Build the child's argv.

    ``-s -E`` rather than ``-I``: we want the isolation ``-I`` gives (no user
    site-packages, environment variables ignored) but *not* its ``-P``
    behaviour, which removes the script's own directory from ``sys.path``. The
    workspace must stay importable or a multi-file submission cannot import its
    own modules. The supervisor itself still runs under ``-I`` — see the
    Dockerfile — because it imports nothing from the workspace.
    """
    mode = job.get("mode", "script")
    if mode == "script":
        entrypoint = job.get("entrypoint", "main.py")
        if not isinstance(entrypoint, str):
            raise JobError("job.entrypoint must be a string")
        _safe_relative_path(entrypoint)  # validate, ignore result
        return [sys.executable, "-s", "-E", "-B", "-u", entrypoint]
    if mode == "pytest":
        args = job.get("pytest_args") or ["-q", "--color=no", "-p", "no:cacheprovider"]
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise JobError("job.pytest_args must be a list of strings")
        # Reject option injection that could reach outside the workspace.
        for arg in args:
            if arg.startswith("-") and arg.split("=")[0] in {"--rootdir", "--basetemp"}:
                raise JobError(f"disallowed pytest argument: {arg}")
            if not arg.startswith("-"):
                _safe_relative_path(arg)
        return [sys.executable, "-s", "-E", "-B", "-m", "pytest", *args]
    raise JobError(f"unsupported mode: {mode!r}")


def _truncate(data: bytes, limit: int) -> tuple[str, bool]:
    truncated = len(data) > limit
    if truncated:
        data = data[:limit]
    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += f"\n... output truncated at {limit} bytes ...\n"
    return text, truncated


def _kill_tree(process: subprocess.Popen[bytes]) -> None:
    """SIGTERM the child's process group, then SIGKILL after a grace period."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            process.wait(timeout=GRACE_PERIOD_SECONDS)
            return
        except subprocess.TimeoutExpired:
            continue


def run(job: dict) -> dict:
    timeout = float(job.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)
    timeout = max(0.5, min(timeout, 120.0))
    max_output = int(job.get("max_output_bytes") or DEFAULT_MAX_OUTPUT_BYTES)
    max_output = max(1024, min(max_output, 4 * 1024 * 1024))
    stdin_data = (job.get("stdin") or "").encode("utf-8")

    _materialise(job.get("files", {}))
    command = _build_command(job)

    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(WORKSPACE),
        "TMPDIR": str(WORKSPACE),
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONHASHSEED": "0",
        # Signals to learner code (and our own examples) that it is sandboxed.
        "PYFORGE_SANDBOX": "1",
        "LC_ALL": "C.UTF-8",
    }

    started = time.monotonic()
    process = subprocess.Popen(  # noqa: S603 - argv list, no shell, fixed interpreter
        command,
        cwd=str(WORKSPACE),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=_apply_child_limits,  # noqa: PLW1509 - single-threaded supervisor
    )

    timed_out = False
    try:
        out, err = process.communicate(input=stdin_data, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(process)
        out, err = process.communicate()
    duration_ms = int((time.monotonic() - started) * 1000)

    stdout, stdout_truncated = _truncate(out or b"", max_output)
    stderr, stderr_truncated = _truncate(err or b"", max_output)
    if timed_out:
        stderr += (
            f"\nExecution stopped: the program exceeded the {timeout:g}s time limit.\n"
            "This usually means an infinite loop or a blocking call.\n"
        )

    return {
        "ok": not timed_out and process.returncode == 0,
        "exit_code": -1 if timed_out else int(process.returncode or 0),
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "error": None,
    }


def main() -> None:
    try:
        job = _read_job()
    except JobError as exc:
        _fail(str(exc))
        return
    try:
        _emit(run(job))
    except JobError as exc:
        _fail(str(exc))
    except Exception as exc:  # noqa: BLE001 - never let the supervisor crash silently
        _fail(f"runner internal error: {type(exc).__name__}: {exc}", exit_code=3)


if __name__ == "__main__":
    main()
