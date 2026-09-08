# ---------------------------------------------------------------------------
# PyForge hardened Python runner.
#
# This image executes UNTRUSTED learner code. It is deliberately minimal:
# no shell utilities beyond what CPython needs, no package manager at runtime,
# no network clients, and a non-root user that owns nothing writable.
#
# Runtime isolation (network, memory, CPU, PIDs, read-only rootfs, capability
# drop, no-new-privileges) is applied by the caller — see
# backend/app/execution/docker_runner.py and docs/SECURITY.md.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PIP_NO_CACHE_DIR=1

# Test tooling is the only third-party dependency: exercises are graded with pytest.
RUN pip install --no-cache-dir "pytest==8.3.3" \
 && rm -rf /var/lib/apt/lists/* /root/.cache /tmp/*

# Unprivileged, no login shell, no home write access.
RUN groupadd --gid 5000 runner \
 && useradd --uid 5000 --gid 5000 --no-create-home --shell /usr/sbin/nologin runner

# /workspace is the only path the caller mounts writable (as a tmpfs).
RUN mkdir -p /workspace && chown runner:runner /workspace

COPY --chown=root:root entrypoint.py /opt/pyforge/entrypoint.py
RUN chmod 0555 /opt/pyforge/entrypoint.py

USER runner
WORKDIR /workspace

# Fail closed: with no arguments the runner exits rather than dropping to a shell.
ENTRYPOINT ["python", "-I", "-B", "/opt/pyforge/entrypoint.py"]
CMD []
