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

/** Where the vendored Python modules live, relative to the deployed base path. */
const CONTENT_ROOT = `${import.meta.env.BASE_URL}content`;

/** Run Python in the browser and return the same shape the API used to return. */
export async function run(options: RunOptions): Promise<ExecuteResponse> {
  const { files, mode = 'script', entrypoint = 'main.py', stdin = '' } = options;
  const response = await dispatch({
    op: 'run',
    files,
    mode,
    entrypoint,
    pytestArgs: mode === 'pytest' ? PYTEST_ARGS : [],
    stdin,
    maxOutputBytes: MAX_OUTPUT_BYTES,
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

/**
 * Grade a submission using the vendored backend grader.
 *
 * Runs in the same interpreter as execution, so a graded submission costs one
 * Pyodide boot rather than two.
 */
export async function grade(payload: {
  exercise: unknown;
  files: Record<string, string>;
  execution: unknown;
  selected_index: number | null;
}): Promise<{
  status: string;
  score: number;
  checks: unknown[];
  feedback: string;
  misconceptions: string[];
}> {
  const response = await dispatch({ op: 'grade', payload, files: {} });
  if (response.error) throw new Error(response.error);
  return response.result as never;
}

/** Review files using the vendored code-review engine. */
export async function review(files: Record<string, string>): Promise<unknown> {
  const response = await dispatch({ op: 'review', files });
  if (response.error) throw new Error(response.error);
  return response.result;
}

/** Post one job to the worker and await its reply, enforcing the timeout. */
async function dispatch(job: {
  op: 'run' | 'grade' | 'review';
  files: Record<string, string>;
  mode?: 'script' | 'pytest';
  entrypoint?: string;
  pytestArgs?: string[];
  stdin?: string;
  maxOutputBytes?: number;
  payload?: unknown;
}): Promise<WorkerResponse> {
  worker ??= spawnWorker();
  const id = crypto.randomUUID();
  const started = performance.now();

  // A cold interpreter needs a far longer budget than the code itself does, so
  // the first job is allowed the boot grace on top of the execution timeout.
  const budget = booted ? TIMEOUT_MS : TIMEOUT_MS + BOOT_GRACE_MS;

  return new Promise<WorkerResponse>((resolve) => {
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
      op: job.op,
      files: job.files,
      mode: job.mode ?? 'script',
      entrypoint: job.entrypoint ?? 'main.py',
      pytestArgs: job.pytestArgs ?? [],
      stdin: job.stdin ?? '',
      maxOutputBytes: job.maxOutputBytes ?? MAX_OUTPUT_BYTES,
      contentRoot: CONTENT_ROOT,
      payload: job.payload,
    } satisfies WorkerRequest);
  });
}
