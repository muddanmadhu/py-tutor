/**
 * The interactive code editor.
 *
 * Monaco, plus multi-file tabs, a run/test/submit toolbar and an output
 * console. It owns no persistence: the parent decides what to do with the
 * files, which is what lets the same component serve lessons, the Code Lab and
 * the project IDE.
 */

import Editor, { type OnMount } from '@monaco-editor/react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { execution } from '@/api/endpoints';
import { ApiError } from '@/api/client';
import type { ExecuteResponse } from '@/api/types';
import { warmUp } from '@/execution/runner';
import { useTheme } from '@/state/theme';

export interface CodeEditorProps {
  files: Record<string, string>;
  onFilesChange: (files: Record<string, string>) => void;
  entrypoint?: string;
  height?: number;
  /** Context sent with run events so analytics can attribute the activity. */
  lessonSlug?: string;
  exerciseSlug?: string;
  /** Rendered to the right of the Run button. */
  actions?: React.ReactNode;
  /** Restores the original starter files. */
  onReset?: () => void;
  readOnly?: boolean;
  /** Show a "Run tests" button that executes pytest over the workspace. */
  allowTests?: boolean;
  onRunComplete?: (result: ExecuteResponse) => void;
}

export function CodeEditor({
  files,
  onFilesChange,
  entrypoint = 'main.py',
  height = 340,
  lessonSlug,
  exerciseSlug,
  actions,
  onReset,
  readOnly = false,
  allowTests = false,
  onRunComplete,
}: CodeEditorProps) {
  const { theme } = useTheme();
  const names = Object.keys(files);
  const [activeFile, setActiveFile] = useState<string>(
    () => (entrypoint in files ? entrypoint : (names[0] ?? '')),
  );
  const [result, setResult] = useState<ExecuteResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [engineError, setEngineError] = useState<string | null>(null);
  const consoleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeFile || !(activeFile in files)) {
      setActiveFile(entrypoint in files ? entrypoint : (Object.keys(files)[0] ?? ''));
    }
  }, [files, activeFile, entrypoint]);

  // Python runs in the browser, and booting the interpreter is a multi-megabyte
  // download. Start it as soon as an editor appears so the learner is reading
  // the prompt while it loads, rather than waiting after pressing Run.
  useEffect(() => {
    warmUp();
  }, []);

  const run = useCallback(
    async (mode: 'script' | 'pytest') => {
      setRunning(true);
      setEngineError(null);
      try {
        const response = await execution.run({
          files,
          entrypoint,
          mode,
          lesson_slug: lessonSlug,
          exercise_slug: exerciseSlug,
        });
        setResult(response);
        onRunComplete?.(response);
      } catch (error) {
        setResult(null);
        setEngineError(
          error instanceof ApiError
            ? error.message
            : 'Could not reach the execution engine. Check your connection and try again.',
        );
      } finally {
        setRunning(false);
        requestAnimationFrame(() => consoleRef.current?.scrollIntoView({ block: 'nearest' }));
      }
    },
    [files, entrypoint, lessonSlug, exerciseSlug, onRunComplete],
  );

  const handleMount: OnMount = (editor, monaco) => {
    // Ctrl/Cmd+Enter runs — the shortcut people expect from a REPL.
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => void run('script'));
  };

  const updateActiveFile = (value: string | undefined) => {
    if (!activeFile) return;
    onFilesChange({ ...files, [activeFile]: value ?? '' });
  };

  return (
    <div className="editor-shell">
      {names.length > 1 && (
        <div className="file-tabs" role="tablist" aria-label="Project files">
          {names.map((name) => (
            <button
              key={name}
              type="button"
              role="tab"
              aria-selected={name === activeFile}
              className={`file-tab${name === activeFile ? ' active' : ''}`}
              onClick={() => setActiveFile(name)}
            >
              {name}
            </button>
          ))}
        </div>
      )}

      <div className="editor-surface">
        <Editor
          height={height}
          language="python"
          theme={theme === 'dark' ? 'vs-dark' : 'light'}
          path={activeFile}
          value={activeFile ? (files[activeFile] ?? '') : ''}
          onChange={updateActiveFile}
          onMount={handleMount}
          options={{
            readOnly,
            fontSize: 13.5,
            fontFamily: 'var(--font-mono)',
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            tabSize: 4,
            insertSpaces: true,
            automaticLayout: true,
            renderWhitespace: 'selection',
            rulers: [88],
            bracketPairColorization: { enabled: true },
            suggestOnTriggerCharacters: true,
            quickSuggestions: { other: true, comments: false, strings: false },
            padding: { top: 12, bottom: 12 },
            accessibilitySupport: 'auto',
          }}
          loading={<div className="empty">Loading editor…</div>}
        />
      </div>

      <div className="editor-toolbar">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => void run('script')}
          disabled={running || readOnly}
        >
          {running ? <span className="spinner" aria-hidden /> : '▶'} Run
          <kbd className="visually-hidden">Control Enter</kbd>
        </button>

        {allowTests && (
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => void run('pytest')}
            disabled={running}
          >
            Run tests
          </button>
        )}

        {onReset && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onReset}>
            Reset
          </button>
        )}

        <div className="grow" />
        {actions}
      </div>

      {(result || engineError) && (
        <div className="console" ref={consoleRef}>
          <div className="console-header">
            <span>
              Output
              {result && !engineError && (
                <>
                  {' · '}
                  {result.duration_ms} ms · exit {result.exit_code}
                </>
              )}
            </span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setResult(null);
                setEngineError(null);
              }}
            >
              Clear
            </button>
          </div>

          {engineError && <pre className="console-output is-error">{engineError}</pre>}

          {result?.stdout && <pre className="console-output">{result.stdout}</pre>}

          {result?.stderr && <pre className="console-output is-error">{result.stderr}</pre>}

          {result && !result.stdout && !result.stderr && !engineError && (
            <pre className="console-output faint">
              (no output — the program ran but printed nothing)
            </pre>
          )}

          {result?.error_explanation && (
            <div className="alert alert-warning" style={{ margin: 'var(--space-3)' }}>
              <strong>What went wrong</strong>
              <div className="small" style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
                {result.error_explanation}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
