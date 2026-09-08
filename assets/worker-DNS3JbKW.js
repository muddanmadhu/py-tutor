(function(){"use strict";const d="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/",p=String.raw`
import contextlib, io, json, os, pathlib, shutil, sys, time, traceback

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


def _learner_traceback(exc_type, exc_value, exc_tb, entrypoint):
    """Format a traceback that starts at the learner's code.

    The driver's own frames sit on top of every traceback and are noise to
    someone learning Python, so frames are dropped until the first one that
    belongs to a file in the workspace. A SyntaxError has no frames at all —
    it is raised at compile time — so the header is only emitted when there is
    something under it.
    """
    frames = traceback.extract_tb(exc_tb)
    for index, frame in enumerate(frames):
        if frame.filename == entrypoint or frame.filename.startswith(WORKSPACE):
            frames = frames[index:]
            break
    else:
        frames = []

    parts = []
    if frames:
        parts.append("Traceback (most recent call last):\n")
        parts.extend(traceback.format_list(frames))
    parts.extend(traceback.format_exception_only(exc_type, exc_value))
    return "".join(parts)


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

                args = list(job.get("pytest_args", []))
                sys.argv = ["pytest", *args]
                exit_code = int(pytest.main(args))
            else:
                entrypoint = job.get("entrypoint", "main.py")
                sys.argv = [entrypoint]
                try:
                    # Compiled and exec'd rather than runpy.run_path, so the
                    # traceback carries the learner's filename and no runpy
                    # internals for them to wade through.
                    source = pathlib.Path(entrypoint).read_text(encoding="utf-8")
                    code = compile(source, entrypoint, "exec")
                    exec(code, {"__name__": "__main__", "__file__": entrypoint})
                except SystemExit as exc:
                    # A deliberate sys.exit() is the program's own exit code.
                    exit_code = 0 if exc.code is None else int(exc.code or 0)
                except BaseException:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    err.write(_learner_traceback(exc_type, exc_value, exc_tb, entrypoint))
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
`;let c=null;function _(){return c??(c=(async()=>{const e=await(await import(`${d}pyodide.mjs`)).loadPyodide({indexURL:d});return await e.loadPackage(["pytest"]),e.runPython(p),e})()),c}const n=new Map;function u(s,e,r){const t=n.get(r);if(t)return t;const o=(async()=>{const a=await fetch(`${e}/${r}.py`);if(!a.ok)throw new Error(`Could not load ${r}.py (HTTP ${a.status}).`);s.runPython(await a.text())})();return n.set(r,o),o.catch(()=>n.delete(r)),o}function l(s,e,r){return{id:s,ok:!0,exitCode:0,stdout:"",stderr:"",timedOut:!1,durationMs:Math.round(performance.now()-e),stdoutTruncated:!1,stderrTruncated:!1,error:null,result:r}}self.addEventListener("message",s=>{const e=s.data,r=performance.now();(async()=>{try{const t=await _(),o=e.contentRoot??"";if(e.op==="grade"){await u(t,o,"grader");const i=t.globals.get("grade_submission")(t.toPy(e.payload));self.postMessage(l(e.id,r,JSON.parse(i)));return}if(e.op==="review"){await u(t,o,"reviewer");const i=t.globals.get("review_submission")(t.toPy(e.files));self.postMessage(l(e.id,r,JSON.parse(i)));return}const f=t.globals.get("run_job")(t.toPy({files:e.files,mode:e.mode,entrypoint:e.entrypoint,pytest_args:e.pytestArgs,stdin:e.stdin,max_output_bytes:e.maxOutputBytes})),m=JSON.parse(f);self.postMessage({...m,id:e.id,timedOut:!1})}catch(t){self.postMessage({id:e.id,ok:!1,exitCode:-2,stdout:"",stderr:"",timedOut:!1,durationMs:Math.round(performance.now()-r),stdoutTruncated:!1,stderrTruncated:!1,error:t instanceof Error?t.message:"The Python engine failed to start."})}})()})})();
//# sourceMappingURL=worker-DNS3JbKW.js.map
