"""Container-isolation tests.

These verify the security properties the platform actually depends on, and they
need a working Docker daemon plus the ``pyforge/runner`` image. They are skipped
automatically when either is absent; CI runs them in a dedicated job.

    make runner-image && pytest -m docker -v
"""

from __future__ import annotations

import os

import pytest

from app.core.config import Settings
from app.execution.base import ExecutionJob

pytestmark = pytest.mark.docker


@pytest.fixture(scope="module")
def docker_executor():
    """A Docker executor, or a skip when the daemon or image is unavailable."""
    from app.execution.docker_runner import DockerExecutor

    settings = Settings(
        env="test",
        secret_key="docker-isolation-test-secret-key-long-enough",
        executor="docker",
        runner_image=os.getenv("PYFORGE_RUNNER_IMAGE", "pyforge/runner:latest"),
        exec_timeout_seconds=10,
    )
    executor = DockerExecutor(settings)
    if not executor.healthy():
        pytest.skip("Docker daemon or pyforge/runner image unavailable")
    return executor


class TestContainerIsolation:
    def test_runs_code(self, docker_executor):
        result = docker_executor.run(ExecutionJob(files={"main.py": "print('sandboxed')"}))
        assert result.ok
        assert result.stdout.strip() == "sandboxed"

    def test_no_network_access(self, docker_executor):
        """`--network none` must make outbound connections impossible."""
        source = (
            "import socket\n"
            "try:\n"
            "    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
            "    print('NETWORK REACHABLE')\n"
            "except OSError as exc:\n"
            "    print('blocked:', type(exc).__name__)\n"
        )
        result = docker_executor.run(ExecutionJob(files={"main.py": source}))
        assert "NETWORK REACHABLE" not in result.stdout
        assert "blocked" in result.stdout

    def test_dns_resolution_fails(self, docker_executor):
        source = (
            "import socket\n"
            "try:\n"
            "    socket.gethostbyname('example.com')\n"
            "    print('DNS WORKS')\n"
            "except OSError:\n"
            "    print('dns blocked')\n"
        )
        result = docker_executor.run(ExecutionJob(files={"main.py": source}))
        assert "DNS WORKS" not in result.stdout

    def test_root_filesystem_is_read_only(self, docker_executor):
        source = (
            "try:\n"
            "    open('/etc/pyforge-probe', 'w').write('x')\n"
            "    print('ROOTFS WRITABLE')\n"
            "except OSError as exc:\n"
            "    print('read-only:', type(exc).__name__)\n"
        )
        result = docker_executor.run(ExecutionJob(files={"main.py": source}))
        assert "ROOTFS WRITABLE" not in result.stdout

    def test_workspace_is_writable(self, docker_executor):
        source = (
            "from pathlib import Path\n"
            "Path('scratch.txt').write_text('ok')\n"
            "print(Path('scratch.txt').read_text())\n"
        )
        result = docker_executor.run(ExecutionJob(files={"main.py": source}))
        assert result.stdout.strip() == "ok"

    def test_runs_as_a_non_root_user(self, docker_executor):
        result = docker_executor.run(
            ExecutionJob(files={"main.py": "import os\nprint(os.getuid())"})
        )
        assert result.stdout.strip() == "5000"

    def test_memory_limit_is_enforced(self, docker_executor):
        """A deliberate allocation far above the cap must be killed, not swapped."""
        source = "data = bytearray(2_000_000_000)\nprint('ALLOCATED')\n"
        result = docker_executor.run(ExecutionJob(files={"main.py": source}, timeout_seconds=15))
        assert "ALLOCATED" not in result.stdout
        assert not result.ok

    def test_fork_bomb_is_contained(self, docker_executor):
        source = (
            "import os\n"
            "for _ in range(500):\n"
            "    try:\n"
            "        os.fork()\n"
            "    except OSError:\n"
            "        pass\n"
            "print('done')\n"
        )
        result = docker_executor.run(ExecutionJob(files={"main.py": source}, timeout_seconds=10))
        # The container must terminate one way or another; the host must survive.
        assert result.duration_ms < 30_000

    def test_infinite_loop_is_killed(self, docker_executor):
        result = docker_executor.run(
            ExecutionJob(files={"main.py": "while True: pass"}, timeout_seconds=3)
        )
        assert result.timed_out

    def test_container_is_removed_after_the_run(self, docker_executor):
        import subprocess

        docker_executor.run(ExecutionJob(files={"main.py": "print(1)"}))
        listing = subprocess.run(
            ["docker", "ps", "-a", "--filter", "label=pyforge.role=runner", "-q"],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        assert listing.stdout.strip() == "", "runner containers were left behind"

    def test_path_traversal_in_a_filename_is_refused_before_execution(self, docker_executor):
        from app.core.config import get_settings
        from app.core.errors import ValidationFailure
        from app.execution.base import build_job

        with pytest.raises(ValidationFailure):
            build_job(
                get_settings(),
                files={"../../../etc/cron.d/evil": "x", "main.py": "pass"},
            )
