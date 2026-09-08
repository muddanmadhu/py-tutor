# The Execution Engine

Running arbitrary code submitted by strangers is the single highest-risk thing
this platform does. This document describes how it is contained.

## The contract

```
                        ┌──────────────────────────────────────┐
  build_job(...)  ────►  │ validation (app/execution/base.py)   │
                        │  · relative paths only, no ..        │
                        │  · allowlisted extensions            │
                        │  · file count and total size caps    │
                        │  · entrypoint must exist and be .py  │
                        │  · timeout clamped to configuration  │
                        └───────────────┬──────────────────────┘
                                        │ ExecutionJob (frozen)
                        ┌───────────────▼──────────────────────┐
  executor.run(job) ──► │ backend: docker (prod) | subprocess  │
                        └───────────────┬──────────────────────┘
                                        │ ExecutionResult (frozen)
                                        ▼
                    ok · exit_code · stdout · stderr · timed_out
                    duration_ms · truncation flags · error
```

Validation lives **above** the backends, so every backend enforces the same
rules and a backend is responsible only for isolation. `ExecutionResult` is the
only thing that comes back, and it never raises for learner-caused failures — a
crash, a timeout and a syntax error are all normal results.

## The runner image

`runner/Dockerfile` builds a minimal `python:3.12-slim` image containing CPython,
pytest and one supervisor script. There is no package manager at runtime, no
shell tooling beyond what CPython needs, and no network client library.

`runner/entrypoint.py` is the supervisor. It:

1. reads one JSON job document from stdin
2. materialises the files, re-validating every path against escape
3. applies in-container `rlimit`s (address space, file size, process count)
4. `fork`s the learner's process into a new session (`os.setsid`)
5. captures stdout and stderr through pipes it owns
6. kills the whole process **group** on timeout — SIGTERM, then SIGKILL
7. truncates output and writes one JSON result document to *its own* stdout

The process boundary matters: the child writes to pipes the supervisor owns, so
learner output can never be confused with the result envelope. Anything the
supervisor prints is protocol; anything the child prints is data.

## Isolation applied to every run

`DockerExecutor` launches one throwaway container per run:

| Flag | Stops |
| --- | --- |
| `--network none` | all egress, DNS, and lateral movement |
| `--read-only` | writing anywhere outside the workspace |
| `--tmpfs /workspace:rw,size=32m` | filling the host disk |
| `--memory 256m --memory-swap 256m` | memory exhaustion; equal values disable swap |
| `--cpus 0.5` | starving other learners of CPU |
| `--pids-limit 64` | fork bombs |
| `--cap-drop ALL` | every Linux capability, including `CAP_NET_RAW` |
| `--security-opt no-new-privileges` | setuid escalation |
| `--user 5000:5000` | running as root inside the container |
| `--rm` + explicit `docker rm -f` | container accumulation |

On top of that, this process applies:

* a **wall-clock guard** at `timeout + 15s`, in case the container never starts
  or the daemon wedges
* a **concurrency semaphore** (`PYFORGE_EXEC_MAX_CONCURRENT`) so a burst of
  submissions cannot spawn unbounded containers
* **output truncation** at `PYFORGE_EXEC_MAX_OUTPUT_BYTES`, so
  `print('x' * 10**9)` cannot exhaust API memory
* a **per-user rate limit** (`ExecutionRateLimiter`) before a job is even built

`tests/test_docker_isolation.py` asserts each of these properties against a real
daemon. That suite is the executable form of this document.

## Job and result protocol

Job document (API → runner, over stdin):

```json
{
  "mode": "script",
  "entrypoint": "main.py",
  "files": {"main.py": "print('hi')", "helper.py": "..."},
  "stdin": "",
  "timeout_seconds": 10,
  "max_output_bytes": 65536
}
```

Result document (runner → API, over stdout):

```json
{
  "ok": true,
  "exit_code": 0,
  "stdout": "hi\n",
  "stderr": "",
  "timed_out": false,
  "duration_ms": 31,
  "stdout_truncated": false,
  "stderr_truncated": false,
  "error": null
}
```

`mode: "pytest"` runs the suite instead of a script, and is how exercises and
project acceptance tests are graded. Learner files and hidden test files are
merged in the same workspace, with hidden files applied last so a learner cannot
overwrite the tests that grade them.

## The development backend

`SubprocessExecutor` exists so the platform runs on a laptop without Docker. It
applies POSIX resource limits and a wall-clock timeout in a temporary directory,
and it is genuinely useful for development.

It does **not** provide network isolation, filesystem isolation or kernel-level
containment. `Settings._enforce_production_invariants` refuses to start with
`PYFORGE_EXECUTOR=subprocess` when `PYFORGE_ENV=production`, and the constructor
raises as a second line of defence. Do not weaken either check.

The API surfaces which backend is live at `GET /api/execution/health`, and the
UI shows a warning badge when isolation is off, so nobody can be confused about
what they are running.

## Failure modes and how they surface

| Failure | Learner sees | Recorded as |
| --- | --- | --- |
| Infinite loop | "exceeded the Ns time limit" + guidance | `timed_out`, misconception `infinite-loop` |
| Memory exhaustion | non-zero exit, MemoryError or a kill | `ok: false` |
| Fork bomb | container killed by the PID cap | `ok: false` |
| Network attempt | `OSError` from the socket call | normal traceback |
| Daemon unavailable | "the execution engine is offline" | `error` set, `exit_code: -2` |
| Engine saturated | "please retry in a moment" | `error` set |
| Malformed job | 422 with the offending field | never reaches a container |

Note the last row: a rejected job never starts a container at all, which is why
path-traversal tests belong in `test_execution.py` rather than in the Docker
suite.

## Performance

Container start dominates: roughly 200–400 ms of the wall time for a run that
executes in 30 ms. Options, in the order we would reach for them:

1. **Warm pool.** Keep N idle containers and `docker exec` into them. Faster, but
   it weakens the guarantee that every run starts from a pristine filesystem.
2. **Queue the work.** Redis plus dedicated workers, so a burst queues rather
   than saturating the semaphore. This is the recommended first step at scale.
3. **gVisor / Firecracker.** Stronger isolation with a comparable start cost.
   Worth it if the platform is ever exposed to genuinely adversarial users.

Measure before choosing: for a learner, 400 ms is imperceptible, and a warm pool
trades a security property for latency nobody noticed.

## Extending the engine

To add a backend, implement the `Executor` protocol:

```python
class MyExecutor:
    name = "my-backend"

    def healthy(self) -> bool: ...
    def run(self, job: ExecutionJob) -> ExecutionResult: ...
```

Register it in `app/execution/factory.py`, add an `ExecutorKind` member, and add
its isolation guarantees to `tests/test_docker_isolation.py`-style tests. Do not
add a backend without tests that prove the network and filesystem claims — an
unverified isolation claim is worse than no claim.
