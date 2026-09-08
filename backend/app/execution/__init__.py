"""Sandboxed Python execution engine.

Two backends implement the same :class:`~app.execution.base.Executor` protocol:

* :class:`~app.execution.docker_runner.DockerExecutor` — the production path.
  One throwaway container per run with no network, a read-only root filesystem,
  dropped capabilities and hard CPU/memory/PID caps.
* :class:`~app.execution.subprocess_runner.SubprocessExecutor` — a development
  convenience that applies POSIX resource limits to a child process. It does
  **not** provide network or filesystem isolation and is refused in production
  by :class:`app.core.config.Settings`.

See ``docs/EXECUTION_ENGINE.md`` for the full design and threat model.
"""

from app.execution.base import ExecutionJob, ExecutionResult, Executor
from app.execution.factory import get_executor

__all__ = ["ExecutionJob", "ExecutionResult", "Executor", "get_executor"]
