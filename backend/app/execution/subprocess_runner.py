"""Local subprocess execution — development only.

This backend exists so the platform can be run on a laptop without Docker. It
applies POSIX resource limits (address space, file size, process count, CPU) and
a wall-clock timeout, and it runs in a throwaway temporary directory.

It does **not** provide:

* network isolation — learner code can open sockets
* filesystem isolation — learner code can read anything the API user can read
* kernel-level containment

:class:`app.core.config.Settings` refuses to start with this backend in
production. Do not weaken that check.
"""

from __future__ import annotations

import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.execution.base import ExecutionJob, ExecutionResult
from app.models.enums import ExecutionMode

logger = get_logger(__name__)

_MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024
_MAX_PROCESSES = 48
_GRACE_SECONDS = 1.0


class SubprocessExecutor:
    """Runs learner code as a resource-limited local child process."""

    name = "subprocess"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._semaphore = threading.BoundedSemaphore(self._settings.exec_max_concurrent)
        if self._settings.is_production:  # pragma: no cover - config forbids this
            raise RuntimeError("SubprocessExecutor must never be used in production")
        logger.warning("using the subprocess executor: learner code is NOT isolated from this host")

    def healthy(self) -> bool:
        """Report availability: this backend only needs the running interpreter."""
        return True

    def run(self, job: ExecutionJob) -> ExecutionResult:
        """Execute ``job`` in a temporary directory."""
        if not self._semaphore.acquire(timeout=30):
            return ExecutionResult.infrastructure_failure(
                "The execution engine is saturated. Please retry in a moment.",
                backend=self.name,
            )
        workspace = Path(tempfile.mkdtemp(prefix="pyforge-run-"))
        try:
            return self._execute(job, workspace)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
            self._semaphore.release()

    # -- internals ----------------------------------------------------------

    def _execute(self, job: ExecutionJob, workspace: Path) -> ExecutionResult:
        for name, content in job.files.items():
            target = workspace / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        # `-s -E`, not `-I`: isolated mode also implies `-P`, which drops the
        # script's directory from sys.path and would break multi-file
        # submissions. See runner/entrypoint.py for the same reasoning.
        if job.mode is ExecutionMode.SCRIPT:
            command = [sys.executable, "-s", "-E", "-B", "-u", job.entrypoint]
        else:
            command = [
                sys.executable,
                "-s",
                "-E",
                "-B",
                "-m",
                "pytest",
                *(job.pytest_args or ("-q", "--color=no", "-p", "no:cacheprovider")),
            ]

        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(workspace),
            "TMPDIR": str(workspace),
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYFORGE_SANDBOX": "1",
            "LC_ALL": "C.UTF-8",
        }

        started = time.monotonic()
        try:
            process = subprocess.Popen(  # noqa: S603 - fixed interpreter, argv list
                command,
                cwd=workspace,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=self._apply_limits(job.timeout_seconds),  # noqa: PLW1509
            )
        except OSError as exc:
            return ExecutionResult.infrastructure_failure(
                f"Could not start the interpreter: {exc}", backend=self.name
            )

        timed_out = False
        try:
            out, err = process.communicate(
                input=job.stdin.encode("utf-8"), timeout=job.timeout_seconds
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill_tree(process)
            out, err = process.communicate()

        duration_ms = int((time.monotonic() - started) * 1000)
        limit = self._settings.exec_max_output_bytes
        stdout, stdout_truncated = self._truncate(out or b"", limit)
        stderr, stderr_truncated = self._truncate(err or b"", limit)
        if timed_out:
            stderr += (
                f"\nExecution stopped: the program exceeded the {job.timeout_seconds:g}s "
                "time limit.\nThis usually means an infinite loop or a blocking call.\n"
            )

        return ExecutionResult(
            ok=not timed_out and process.returncode == 0,
            exit_code=-1 if timed_out else int(process.returncode or 0),
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            duration_ms=duration_ms,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            meta={"backend": self.name, "isolated": False},
        )

    def _apply_limits(self, timeout_seconds: float):  # type: ignore[no-untyped-def]
        """Build the ``preexec_fn`` that constrains the child."""
        memory_bytes = self._settings.exec_memory_mb * 1024 * 1024
        cpu_seconds = max(1, int(timeout_seconds) + 1)

        def _limits() -> None:
            os.setsid()
            # macOS refuses RLIMIT_AS for the interpreter itself; degrade gracefully.
            for which, value in (
                (resource.RLIMIT_AS, memory_bytes),
                (resource.RLIMIT_FSIZE, _MAX_FILE_SIZE_BYTES),
                (resource.RLIMIT_NPROC, _MAX_PROCESSES),
                (resource.RLIMIT_CPU, cpu_seconds),
                (resource.RLIMIT_CORE, 0),
            ):
                try:
                    resource.setrlimit(which, (value, value))
                except (ValueError, OSError):
                    continue

        return _limits

    @staticmethod
    def _kill_tree(process: subprocess.Popen[bytes]) -> None:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(os.getpgid(process.pid), sig)
            except (ProcessLookupError, PermissionError, OSError):
                return
            try:
                process.wait(timeout=_GRACE_SECONDS)
                return
            except subprocess.TimeoutExpired:
                continue

    @staticmethod
    def _truncate(data: bytes, limit: int) -> tuple[str, bool]:
        truncated = len(data) > limit
        if truncated:
            data = data[:limit]
        text = data.decode("utf-8", errors="replace")
        if truncated:
            text += f"\n... output truncated at {limit} bytes ...\n"
        return text, truncated


def _selftest() -> None:  # pragma: no cover - manual smoke check
    """``python -m app.execution.subprocess_runner`` runs a hello-world job."""
    executor = SubprocessExecutor()
    result = executor.run(ExecutionJob(files={"main.py": "print('hello from the sandbox')"}))
    print(json.dumps(result.__dict__, indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover
    _selftest()
