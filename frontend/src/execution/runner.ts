/**
 * Browser-side execution engine.
 *
 * Replaces the server sandbox: learner code runs in the visitor's own browser
 * under Pyodide, so nothing untrusted ever reaches our infrastructure and there
 * is no per-run cost. The trade-off is that results are client-reported, and a
 * determined learner can forge them — acceptable, because the only person they
 * would be cheating is themselves.
 *
 * The worker is owned here rather than by React so that the interpreter (a
 * multi-megabyte download and a slow boot) survives navigation between lessons.
 */

import type { ExecuteResponse } from '@/api/types';
import type { WorkerRequest, WorkerResponse } from './worker';

/** Mirrors `PYFORGE_EXEC_TIMEOUT_SECONDS`; a run past this is a runaway loop. */
const TIMEOUT_MS = 10_000;
/** Mirrors `PYFORGE_EXEC_MAX_OUTPUT_BYTES`. */
const MAX_OUTPUT_BYTES = 65_536;
/** Booting Pyodide and fetching pytest is slow on a cold cache. */
const BOOT_GRACE_MS = 60_000;

/** Matches `PYTEST_ARGS` in `backend/app/services/submissions.py` — the graders parse this output. */
const PYTEST_ARGS = ['-v', '--tb=short', '--color=no', '-p', 'no:cacheprovider'];

export interface RunOptions {
  files: Record<string, string>;
  mode?: 'script' | 'pytest';
  entrypoint?: string;
  stdin?: string;
}

let worker: Worker | null = null;
let booted = false;
let pending: {
  id: string;
  resolve: (value: WorkerResponse) => void;
  timer: ReturnType<typeof setTimeout>;
} | null = null;

function spawnWorker(): Worker {
  const instance = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
  instance.addEventListener('message', (event: MessageEvent<WorkerResponse>) => {
    if (!pending || event.data.id !== pending.id) return;
    clearTimeout(pending.timer);
    booted = true;
    const { resolve } = pending;
    pending = null;
    resolve(event.data);
  });
  return instance;
}

/**
 * Kill the interpreter and start a fresh one.
 *
 * Terminating is the only way to stop a synchronous infinite loop, and it
 * destroys the interpreter with it, so the next run pays the boot cost again.
 */
function recycleWorker(): void {
  worker?.terminate();
  worker = spawnWorker();
  booted = false;
}

/** Start downloading and booting Pyodide before the learner first hits Run. */
export function warmUp(): void {
  worker ??= spawnWorker();
}

/** Whether the interpreter has completed at least one run (i.e. is warm). */
export function isReady(): boolean {
  return booted;
}

/** Run Python in the browser and return the same shape the API used to return. */
export async function run(options: RunOptions): Promise<ExecuteResponse> {
  const { files, mode = 'script', entrypoint = 'main.py', stdin = '' } = options;

  worker ??= spawnWorker();
  const id = crypto.randomUUID();
  const started = performance.now();

  // A cold interpreter needs a far longer budget than the code itself does, so
  // the first run is allowed the boot grace on top of the execution timeout.
  const budget = booted ? TIMEOUT_MS : TIMEOUT_MS + BOOT_GRACE_MS;

  const response = await new Promise<WorkerResponse>((resolve) => {
    const timer = setTimeout(() => {
      pending = null;
      recycleWorker();
      resolve({
        id,
        ok: false,
        exitCode: -1,
        stdout: '',
        stderr: '',
        timedOut: true,
        durationMs: Math.round(performance.now() - started),
        stdoutTruncated: false,
        stderrTruncated: false,
        error: null,
      });
    }, budget);

    pending = { id, resolve, timer };
    worker!.postMessage({
      id,
      files,
      mode,
      entrypoint,
      pytestArgs: mode === 'pytest' ? PYTEST_ARGS : [],
      stdin,
      maxOutputBytes: MAX_OUTPUT_BYTES,
    } satisfies WorkerRequest);
  });

  return {
    ok: response.ok,
    exit_code: response.exitCode,
    stdout: response.stdout,
    stderr: response.stderr,
    timed_out: response.timedOut,
    duration_ms: response.durationMs,
    stdout_truncated: response.stdoutTruncated,
    stderr_truncated: response.stderrTruncated,
    error: response.error,
    error_explanation: null,
  };
}
