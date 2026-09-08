"""Executor selection and rate limiting."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import lru_cache

from app.core.config import ExecutorKind, get_settings
from app.core.errors import RateLimitError
from app.core.logging import get_logger
from app.execution.base import ExecutionJob, ExecutionResult, Executor

logger = get_logger(__name__)


class ClientExecutor:
    """Placeholder backend for deployments where the client runs the code.

    It never executes anything. Callers that can accept a client-reported result
    should check ``Settings.client_side_execution`` and never reach this; anyone
    who does reach it gets a clear infrastructure failure rather than a silent
    pass, which is the safe direction to fail in for a grader.
    """

    name = "client"

    def run(self, job: ExecutionJob) -> ExecutionResult:  # noqa: ARG002 - Executor protocol
        """Refuse ``job``: there is no server-side sandbox to run it in."""
        return ExecutionResult.infrastructure_failure(
            "This deployment runs Python in your browser. Reload the page if the "
            "in-browser engine did not start.",
            backend=self.name,
        )

    def healthy(self) -> bool:
        """Report ready: there is no server-side component that could be down."""
        return True


@lru_cache(maxsize=1)
def get_executor() -> Executor:
    """Return the configured execution backend."""
    settings = get_settings()
    if settings.executor is ExecutorKind.DOCKER:
        from app.execution.docker_runner import get_docker_executor

        return get_docker_executor()

    if settings.executor is ExecutorKind.CLIENT:
        return ClientExecutor()

    from app.execution.subprocess_runner import SubprocessExecutor

    return SubprocessExecutor(settings)


class ExecutionRateLimiter:
    """Per-user sliding-window limiter for sandbox runs.

    In-process by design: it is a cheap guard against a runaway client, not a
    distributed quota. Multi-replica deployments should front this with the
    Redis-backed limiter described in ``docs/DEPLOYMENT.md``.
    """

    def __init__(self, limit_per_minute: int) -> None:
        self._limit = limit_per_minute
        self._window = 60.0
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, user_id: str) -> None:
        """Record a run for ``user_id``, raising if over the allowance."""
        now = time.monotonic()
        with self._lock:
            bucket = self._events[user_id]
            cutoff = now - self._window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry_after = int(self._window - (now - bucket[0])) + 1
                raise RateLimitError(
                    f"You've run code {self._limit} times in the last minute. "
                    "Take a breath and try again shortly.",
                    retry_after_seconds=retry_after,
                )
            bucket.append(now)

    def reset(self, user_id: str | None = None) -> None:
        """Clear recorded events (used by tests)."""
        with self._lock:
            if user_id is None:
                self._events.clear()
            else:
                self._events.pop(user_id, None)


@lru_cache(maxsize=1)
def get_rate_limiter() -> ExecutionRateLimiter:
    """Return the process-wide execution rate limiter."""
    return ExecutionRateLimiter(get_settings().exec_rate_limit_per_minute)
