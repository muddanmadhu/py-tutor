/**
 * Pyodide execution worker.
 *
 * Runs learner Python inside a Web Worker so that the main thread stays
 * responsive and — crucially — so that a program which never terminates can be
 * killed by terminating the worker. Pyodide has no way to interrupt a running
 * synchronous loop from inside itself, so the timeout has to be enforced by
 * whoever owns the worker handle. See `runner.ts`.
 *
 * Pyodide is loaded from the CDN rather than bundled: the full distribution is
 * tens of megabytes, most of which is stdlib the learner may never touch, and
 * the CDN copy is cached across sessions.
 */

/// <reference lib="webworker" />

const PYODIDE_VERSION = '0.26.4';
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

export interface WorkerRequest {
  id: string;
  files: Record<string, string>;
  mode: 'script' | 'pytest';
  entrypoint: string;
  pytestArgs: string[];
  stdin: string;
  maxOutputBytes: number;
}

export interface WorkerResponse {
  id: string;
  ok: boolean;
  exitCode: number;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  durationMs: number;
  stdoutTruncated: boolean;
  stderrTruncated: boolean;
  error: string | null;
}

/**
 * The in-Pyodide driver.
 *
 * Written as Python rather than orchestrated from JS so that stdout/stderr
 * capture, the traceback format and the exit-code convention are identical to
 * what the server-side runner produced — the graders parse this text, so it has
 * to match. Output is truncated on a byte budget, matching
 * `PYFORGE_EXEC_MAX_OUTPUT_BYTES`.
 */
const DRIVER = String.raw`
import contextlib, io, json, os, pathlib, runpy, shutil, sys, time, traceback

WORKSPACE = "/workspace"


def _truncate(text, budget):
    """Trim to a UTF-8 byte budget, reporting whether anything was dropped."""
    raw = text.encode("utf-8", "replace")
    if len(raw) <= budget:
        return text, False
    return raw[:budget].decode("utf-8", "ignore"), True


def _reset_workspace(files):
    """Rebuild the workspace from scratch so runs never leak state into each other."""
    if os.path.isdir(WORKSPACE):
        shutil.rmtree(WORKSPACE)
    os.makedirs(WORKSPACE, exist_ok=True)
    for name, content in files.items():
        target = pathlib.Path(WORKSPACE) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _purge_learner_modules(before):
    """Drop modules imported by the run so the next run re-imports edited files."""
    for name in list(sys.modules):
        if name not in before:
            del sys.modules[name]


def run_job(job):
    files = job["files"]
    mode = job["mode"]
    budget = int(job["max_output_bytes"])

    _reset_workspace(files)

    out, err = io.StringIO(), io.StringIO()
    exit_code = 0
    error = None

    previous_cwd = os.getcwd()
    previous_argv = list(sys.argv)
    previous_stdin = sys.stdin
    modules_before = set(sys.modules)

    os.chdir(WORKSPACE)
    # The workspace must win over anything else on the path, so a learner file
    # named like a stdlib module shadows it exactly as it would locally.
    sys.path.insert(0, WORKSPACE)
    sys.stdin = io.StringIO(job.get("stdin", ""))

    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if mode == "pytest":
                import pytest

                sys.argv = ["pytest", *job.get("pytest_args", [])]
                exit_code = int(pytest.main(list(job.get("pytest_args", []))))
            else:
                entrypoint = job.get("entrypoint", "main.py")
                sys.argv = [entrypoint]
                try:
                    runpy.run_path(entrypoint, run_name="__main__")
                except SystemExit as exc:
                    # A deliberate sys.exit() is the program's own exit code.
                    exit_code = 0 if exc.code is None else int(exc.code or 0)
                except BaseException:
                    # Trim the driver's own frames so the learner sees a traceback
                    # that starts at their code, exactly as the server produced.
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    frames = traceback.extract_tb(exc_tb)
                    keep = [f for f in frames if f.filename not in ("<exec>", __file__)]
                    err.write("Traceback (most recent call last):\n")
                    err.write("".join(traceback.format_list(keep)))
                    err.write("".join(traceback.format_exception_only(exc_type, exc_value)))
                    exit_code = 1
    except BaseException as exc:  # a failure of the harness itself, not of learner code
        error = f"{type(exc).__name__}: {exc}"
        exit_code = -2
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        sys.stdin = previous_stdin
        sys.argv = previous_argv
        os.chdir(previous_cwd)
        if WORKSPACE in sys.path:
            sys.path.remove(WORKSPACE)
        _purge_learner_modules(modules_before)

    stdout, stdout_truncated = _truncate(out.getvalue(), budget)
    stderr, stderr_truncated = _truncate(err.getvalue(), budget)

    return json.dumps({
        "ok": exit_code == 0 and error is None,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": duration_ms,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "error": error,
    })
`;

type Pyodide = {
  runPython: (code: string) => unknown;
  loadPackage: (names: string[]) => Promise<void>;
  globals: { get: (name: string) => (job: unknown) => string };
  toPy: (value: unknown) => unknown;
};

let pyodidePromise: Promise<Pyodide> | null = null;

/** Boot Pyodide once per worker; every later job reuses the interpreter. */
function bootPyodide(): Promise<Pyodide> {
  pyodidePromise ??= (async () => {
    // The CDN URL is deliberately opaque to the bundler — Vite must not try to
    // resolve or inline a 30 MB remote module graph at build time.
    const module = await import(/* @vite-ignore */ `${PYODIDE_CDN}pyodide.mjs`);
    const pyodide: Pyodide = await module.loadPyodide({ indexURL: PYODIDE_CDN });
    // pytest ships as a Pyodide package; loading it up front keeps the first
    // graded submission from paying a surprise download mid-run.
    await pyodide.loadPackage(['pytest']);
    pyodide.runPython(DRIVER);
    return pyodide;
  })();
  return pyodidePromise;
}

self.addEventListener('message', (event: MessageEvent<WorkerRequest>) => {
  const request = event.data;
  const started = performance.now();

  void (async () => {
    try {
      const pyodide = await bootPyodide();
      const runJob = pyodide.globals.get('run_job');
      const raw = runJob(
        pyodide.toPy({
          files: request.files,
          mode: request.mode,
          entrypoint: request.entrypoint,
          pytest_args: request.pytestArgs,
          stdin: request.stdin,
          max_output_bytes: request.maxOutputBytes,
        }),
      );
      const parsed = JSON.parse(raw) as Omit<WorkerResponse, 'id' | 'timedOut'>;
      self.postMessage({ ...parsed, id: request.id, timedOut: false } satisfies WorkerResponse);
    } catch (cause) {
      self.postMessage({
        id: request.id,
        ok: false,
        exitCode: -2,
        stdout: '',
        stderr: '',
        timedOut: false,
        durationMs: Math.round(performance.now() - started),
        stdoutTruncated: false,
        stderrTruncated: false,
        error: cause instanceof Error ? cause.message : 'The Python engine failed to start.',
      } satisfies WorkerResponse);
    }
  })();
});
