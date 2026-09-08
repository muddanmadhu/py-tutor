"""Execution engine contracts and input validation.

Validation lives here, not in the individual backends, so that every backend
enforces the same limits and the same path-safety rules. A backend is then only
responsible for *isolation*, not for deciding what is acceptable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Protocol, runtime_checkable

from app.core.config import Settings
from app.core.errors import ValidationFailure
from app.models.enums import ExecutionMode

#: Only these extensions may be written into a sandbox workspace.
ALLOWED_SUFFIXES = frozenset(
    {".py", ".txt", ".json", ".csv", ".md", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".sql"}
)

#: Extensionless filenames that projects legitimately need (a Dockerfile is a
#: deliverable of the capstone). Compared case-sensitively, and never executed —
#: the sandbox only ever runs the .py entrypoint or pytest.
ALLOWED_EXTENSIONLESS_NAMES = frozenset(
    {"Dockerfile", "Makefile", "LICENSE", "README", "CHANGELOG", "Procfile"}
)

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._/-]+$")


@dataclass(frozen=True, slots=True)
class ExecutionJob:
    """A validated unit of work for the sandbox."""

    files: dict[str, str]
    mode: ExecutionMode = ExecutionMode.SCRIPT
    entrypoint: str = "main.py"
    pytest_args: tuple[str, ...] = ()
    stdin: str = ""
    timeout_seconds: float = 10.0

    def to_payload(self, max_output_bytes: int) -> dict[str, Any]:
        """Render the JSON job document the runner entrypoint consumes."""
        payload: dict[str, Any] = {
            "mode": self.mode.value,
            "files": dict(self.files),
            "stdin": self.stdin,
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": max_output_bytes,
        }
        if self.mode is ExecutionMode.SCRIPT:
            payload["entrypoint"] = self.entrypoint
        else:
            payload["pytest_args"] = list(self.pytest_args) or [
                "-q",
                "--color=no",
                "-p",
                "no:cacheprovider",
            ]
        return payload


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """The outcome of a sandbox run."""

    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    error: str | None = None
    #: Backend-specific diagnostics (container id, backend name, limits applied).
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any], **meta: Any) -> ExecutionResult:
        """Build a result from the runner's JSON response."""
        return cls(
            ok=bool(payload.get("ok")),
            exit_code=int(payload.get("exit_code", 1)),
            stdout=str(payload.get("stdout", "")),
            stderr=str(payload.get("stderr", "")),
            timed_out=bool(payload.get("timed_out")),
            duration_ms=int(payload.get("duration_ms", 0)),
            stdout_truncated=bool(payload.get("stdout_truncated")),
            stderr_truncated=bool(payload.get("stderr_truncated")),
            error=payload.get("error"),
            meta=meta,
        )

    @classmethod
    def infrastructure_failure(cls, message: str, **meta: Any) -> ExecutionResult:
        """Build a result representing a backend failure, not a learner error."""
        return cls(
            ok=False,
            exit_code=-2,
            stdout="",
            stderr="",
            timed_out=False,
            duration_ms=0,
            error=message,
            meta=meta,
        )


@runtime_checkable
class Executor(Protocol):
    """Runs a validated job in isolation and returns its result."""

    name: str

    def run(self, job: ExecutionJob) -> ExecutionResult:
        """Execute ``job``. Must never raise for learner-caused failures."""
        ...

    def healthy(self) -> bool:
        """Whether this backend can currently accept work."""
        ...


def _validate_path(name: str) -> None:
    """Reject path names that could escape or confuse the workspace."""
    if not name or len(name) > 200:
        raise ValidationFailure("File names must be 1–200 characters.", details={"file": name})
    if not _SAFE_NAME.match(name):
        raise ValidationFailure(
            "File names may only contain letters, digits, dot, dash, underscore and '/'.",
            details={"file": name},
        )
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or name.startswith("/"):
        raise ValidationFailure(
            "File paths must be relative and may not traverse upwards.", details={"file": name}
        )
    if path.suffix:
        if path.suffix not in ALLOWED_SUFFIXES:
            raise ValidationFailure(
                f"'{path.suffix}' files are not permitted in the sandbox.",
                details={"file": name, "allowed": sorted(ALLOWED_SUFFIXES)},
            )
    elif path.name not in ALLOWED_EXTENSIONLESS_NAMES:
        raise ValidationFailure(
            "Files need a recognised extension, or one of these exact names: "
            + ", ".join(sorted(ALLOWED_EXTENSIONLESS_NAMES)),
            details={"file": name},
        )


def build_job(
    settings: Settings,
    *,
    files: dict[str, str],
    mode: ExecutionMode = ExecutionMode.SCRIPT,
    entrypoint: str = "main.py",
    pytest_args: tuple[str, ...] = (),
    stdin: str = "",
    timeout_seconds: float | None = None,
) -> ExecutionJob:
    """Validate raw input and produce an :class:`ExecutionJob`.

    Raises
    ------
    ValidationFailure
        If the file set, entrypoint or size exceeds configured limits.
    """
    if not files:
        raise ValidationFailure("Submit at least one file to run.")
    if len(files) > settings.exec_max_files:
        raise ValidationFailure(
            f"At most {settings.exec_max_files} files may be executed at once.",
            details={"submitted": len(files)},
        )

    total_bytes = 0
    for name, content in files.items():
        _validate_path(name)
        if not isinstance(content, str):
            raise ValidationFailure("File contents must be text.", details={"file": name})
        total_bytes += len(content.encode("utf-8"))
    if total_bytes > settings.exec_max_source_bytes:
        raise ValidationFailure(
            f"Total source size exceeds {settings.exec_max_source_bytes} bytes.",
            details={"bytes": total_bytes},
        )

    if mode is ExecutionMode.SCRIPT:
        _validate_path(entrypoint)
        if entrypoint not in files:
            raise ValidationFailure(
                f"Entrypoint '{entrypoint}' is not among the submitted files.",
                details={"entrypoint": entrypoint, "files": sorted(files)},
            )
        if not entrypoint.endswith(".py"):
            raise ValidationFailure("The entrypoint must be a .py file.")

    if len(stdin.encode("utf-8")) > 64 * 1024:
        raise ValidationFailure("Standard input is limited to 64 KiB.")

    timeout = timeout_seconds or settings.exec_timeout_seconds
    timeout = max(0.5, min(float(timeout), settings.exec_timeout_seconds))

    return ExecutionJob(
        files=dict(files),
        mode=mode,
        entrypoint=entrypoint,
        pytest_args=pytest_args,
        stdin=stdin,
        timeout_seconds=timeout,
    )
