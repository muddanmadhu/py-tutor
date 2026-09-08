/** Small shared presentational components. */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import type { Check, MasteryDelta } from '@/api/types';

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="row" role="status" aria-live="polite">
      <span className="spinner" aria-hidden />
      <span className="muted small">{label}…</span>
    </div>
  );
}

export function ErrorNotice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof Error ? error.message : 'Something went wrong loading this page.';
  return (
    <div className="alert alert-error" role="alert">
      <div className="row-between">
        <span>{message}</span>
        {onRetry && (
          <button type="button" className="btn btn-sm" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="empty">
      <p style={{ fontWeight: 600, marginBottom: 4 }}>{title}</p>
      {hint && <p className="small">{hint}</p>}
    </div>
  );
}

/**
 * The mastery bar from the specification, rendered as text so it copies,
 * reads aloud correctly and needs no images.
 */
export function MasteryBar({
  label,
  percent,
  mastered = false,
  weak = false,
}: {
  label: string;
  percent: number;
  mastered?: boolean;
  weak?: boolean;
}) {
  const filled = Math.round((percent / 100) * 20);
  const bar = '█'.repeat(filled) + '░'.repeat(Math.max(0, 20 - filled));
  const tone = mastered ? 'is-mastered' : weak ? 'is-weak' : '';

  return (
    <div style={{ marginBottom: 'var(--space-3)' }}>
      <div className="row-between small">
        <span>{label}</span>
        <span className="muted">{percent}%</span>
      </div>
      <div
        className="meter"
        role="progressbar"
        aria-label={`${label} mastery`}
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`meter-fill ${tone}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="visually-hidden mastery-bar">{bar}</span>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === 'passed' || status === 'completed'
      ? 'badge-success'
      : status === 'failed' || status === 'error' || status === 'timed_out'
        ? 'badge-danger'
        : status === 'partial' || status === 'in_progress' || status === 'attempted'
          ? 'badge-warning'
          : '';
  return <span className={`badge ${tone}`}>{status.replace(/_/g, ' ')}</span>;
}

export function CheckList({ checks }: { checks: Check[] }) {
  if (checks.length === 0) return null;
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {checks.map((check, index) => (
        <li key={`${check.name}-${index}`} className={`check ${check.passed ? 'passed' : 'failed'}`}>
          <span className="check-icon" aria-hidden>
            {check.passed ? '✓' : '✗'}
          </span>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontWeight: 550 }}>
              <span className="visually-hidden">{check.passed ? 'Passed: ' : 'Failed: '}</span>
              {check.name}
            </div>
            {check.message && <div className="small muted">{check.message}</div>}
            {check.diff && <Diff diff={check.diff} />}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Diff({ diff }: { diff: string }) {
  return (
    <pre className="diff">
      {diff.split('\n').map((line, index) => {
        const tone = line.startsWith('+')
          ? 'add'
          : line.startsWith('-')
            ? 'del'
            : line.startsWith('@')
              ? 'meta'
              : '';
        return (
          <div key={index} className={tone}>
            {line}
          </div>
        );
      })}
    </pre>
  );
}

export function MasteryDeltas({ deltas }: { deltas: MasteryDelta[] }) {
  if (deltas.length === 0) return null;
  return (
    <div className="card card-tight" style={{ marginTop: 'var(--space-3)' }}>
      <h4 className="small" style={{ marginBottom: 'var(--space-3)' }}>
        Mastery movement
      </h4>
      {deltas.map((delta) => (
        <div key={delta.concept_slug} className="row-between small" style={{ marginBottom: 6 }}>
          <span>{delta.concept_name}</span>
          <span className={delta.delta >= 0 ? '' : 'muted'}>
            {Math.round(delta.previous * 100)}% → <strong>{Math.round(delta.current * 100)}%</strong>{' '}
            <span style={{ color: delta.delta >= 0 ? 'var(--success)' : 'var(--danger)' }}>
              ({delta.delta >= 0 ? '+' : ''}
              {Math.round(delta.delta * 100)})
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}
