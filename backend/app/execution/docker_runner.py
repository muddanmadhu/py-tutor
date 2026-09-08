"""Docker-backed execution: one disposable container per run.

Why the Docker CLI instead of the SDK
-------------------------------------
The CLI is already required in the API image (it is how operators debug), it
has no Python dependency to keep in step with the daemon API version, and the
exact flags applied are visible in logs and in this file — which matters for a
control that is load-bearing for security.

Isolation applied to every run
------------------------------
``--network none``          no DNS, no sockets, no egress
``--read-only``             immutable root filesystem
``--tmpfs /workspace``      the only writable path, capped, ``noexec`` is *not*
                            set because CPython must map its own temp files
``--memory`` / ``--memory-swap`` equal values disable swap entirely
``--cpus``                  CFS quota
``--pids-limit``            blocks fork bombs
``--cap-drop ALL``          no capabilities at all
``--security-opt no-new-privileges`` setuid binaries cannot escalate
``--user 5000:5000``        non-root
``--rm``                    the daemon reaps the container even on failure

A wall-clock guard in this process backstops the in-container timeout, and a
semaphore bounds how many runs may be in flight at once.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
import uuid
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.execution.base import ExecutionJob, ExecutionResult

logger = get_logger(__name__)

#: Extra seconds allowed for container start/stop before we kill it ourselves.
_STARTUP_GRACE_SECONDS = 15.0
#: Cap on the writable tmpfs mounted at /workspace.
_WORKSPACE_TMPFS_MB = 32


class DockerExecutor:
    """Runs learner code inside a hardened, disposable container."""

    name = "docker"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._semaphore = threading.BoundedSemaphore(self._settings.exec_max_concurrent)
        self._docker = shutil.which("docker") or "docker"

    # -- public API ---------------------------------------------------------

    def healthy(self) -> bool:
        """Whether the daemon responds and the runner image is present."""
        try:
            probe = subprocess.run(  # noqa: S603 - fixed argv, no shell
                [self._docker, "image", "inspect", self._settings.runner_image],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return probe.returncode == 0

    def run(self, job: ExecutionJob) -> ExecutionResult:
        """Execute ``job`` in a fresh container."""
        if not self._semaphore.acquire(timeout=30):
            return ExecutionResult.infrastructure_failure(
                "The execution engine is saturated. Please retry in a moment.",
                backend=self.name,
            )
        container_name = f"pyforge-run-{uuid.uuid4().hex[:16]}"
        try:
            return self._run_container(job, container_name)
        finally:
            self._force_remove(container_name)
            self._semaphore.release()

    # -- internals ----------------------------------------------------------

    def _command(self, container_name: str) -> list[str]:
        settings = self._settings
        memory = f"{settings.exec_memory_mb}m"
        return [
            self._docker,
            "run",
            "--rm",
            "--interactive",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            f"/workspace:rw,size={_WORKSPACE_TMPFS_MB}m,mode=1777",
            "--memory",
            memory,
            "--memory-swap",
            memory,  # equal to --memory ⇒ swap disabled
            "--cpus",
            str(settings.exec_cpus),
            "--pids-limit",
            str(settings.exec_pids_limit),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "5000:5000",
            "--workdir",
            "/workspace",
            "--env",
            "PYFORGE_SANDBOX=1",
            "--label",
            "pyforge.role=runner",
            settings.runner_image,
        ]

    def _run_container(self, job: ExecutionJob, container_name: str) -> ExecutionResult:
        payload = json.dumps(job.to_payload(self._settings.exec_max_output_bytes))
        wall_clock_limit = job.timeout_seconds + _STARTUP_GRACE_SECONDS
        started = time.monotonic()

        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                self._command(container_name),
                input=payload.encode("utf-8"),
                capture_output=True,
                timeout=wall_clock_limit,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "sandbox exceeded the outer wall-clock guard",
                extra={"container": container_name, "limit": wall_clock_limit},
            )
            return ExecutionResult(
                ok=False,
                exit_code=-1,
                stdout="",
                stderr=(
                    "Execution was stopped by the platform: the run did not finish within "
                    f"{wall_clock_limit:g}s."
                ),
                timed_out=True,
                duration_ms=int((time.monotonic() - started) * 1000),
                meta={"backend": self.name, "guard": "outer_wall_clock"},
            )
        except FileNotFoundError:
            return ExecutionResult.infrastructure_failure(
                "Docker is not available on this host; the execution engine is offline.",
                backend=self.name,
            )
        except OSError as exc:
            logger.exception("failed to launch sandbox container")
            return ExecutionResult.infrastructure_failure(
                f"Could not start the execution sandbox: {exc}", backend=self.name
            )

        raw = completed.stdout.decode("utf-8", errors="replace").strip()
        if not raw:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            logger.error(
                "sandbox produced no result envelope",
                extra={"container": container_name, "docker_stderr": detail[:2000]},
            )
            return ExecutionResult.infrastructure_failure(
                "The execution sandbox did not return a result.",
                backend=self.name,
                docker_stderr=detail[:2000],
            )

        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("sandbox returned malformed JSON", extra={"container": container_name})
            return ExecutionResult.infrastructure_failure(
                "The execution sandbox returned an unreadable result.", backend=self.name
            )

        return ExecutionResult.from_payload(
            envelope,
            backend=self.name,
            container=container_name,
            image=self._settings.runner_image,
            memory_mb=self._settings.exec_memory_mb,
            cpus=self._settings.exec_cpus,
        )

    def _force_remove(self, container_name: str) -> None:
        """Best-effort cleanup.

        ``--rm`` handles the normal path; this catches containers orphaned by a
        daemon hiccup or by our own outer timeout killing the CLI mid-run.
        """
        try:
            subprocess.run(  # noqa: S603 - fixed argv, no shell
                [self._docker, "rm", "--force", container_name],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            logger.debug("cleanup of %s failed (likely already gone)", container_name)


@lru_cache(maxsize=1)
def get_docker_executor() -> DockerExecutor:
    """Return the shared Docker executor (its semaphore must be process-wide)."""
    return DockerExecutor()
