/** Code Lab, Python Reference, AI Tutor, Progress, Interview and Settings. */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError } from '@/api/client';
import {
  auth,
  codeReview,
  execution,
  interview,
  progress,
  reference,
  tutor,
} from '@/api/endpoints';
import type { MasteryItem, ReviewResponse } from '@/api/types';
import { CodeEditor } from '@/components/CodeEditor';
import {
  EmptyState,
  ErrorNotice,
  Markdown,
  MasteryBar,
  Spinner,
  StatusBadge,
} from '@/components/ui';
import { useAuth } from '@/state/auth';

/* ------------------------------------------------------------------ lab */

const LAB_STARTER = `"""Code Lab — a scratchpad with a real Python sandbox.

Everything you run here executes in an isolated container: no network,
capped memory and CPU, and a hard time limit.
"""


def main() -> None:
    print("Hello from the sandbox")


if __name__ == "__main__":
    main()
`;

export function CodeLabPage() {
  const [files, setFiles] = useState<Record<string, string>>({ 'main.py': LAB_STARTER });
  const [newFileName, setNewFileName] = useState('');
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [snippetName, setSnippetName] = useState('');

  const { data: health } = useQuery({ queryKey: ['exec-health'], queryFn: execution.health });
  const { data: snippets, refetch: refetchSnippets } = useQuery({
    queryKey: ['snippets'],
    queryFn: execution.snippets,
  });

  const runReview = async () => {
    setReviewing(true);
    try {
      setReview(await codeReview(files));
    } finally {
      setReviewing(false);
    }
  };

  const save = async () => {
    const name = snippetName.trim();
    if (!name) return;
    await execution.saveSnippet(name, files, 'main.py');
    setSnippetName('');
    await refetchSnippets();
  };

  return (
    <div style={{ padding: 'var(--space-5)' }} className="stack">
      <header className="row-between wrap">
        <div>
          <h1 style={{ marginBottom: 4 }}>Code Lab</h1>
          <p className="muted" style={{ margin: 0 }}>
            A multi-file Python workspace with a sandboxed runtime.
          </p>
        </div>
        {health && (
          <span className={`badge ${health.isolated ? 'badge-success' : 'badge-warning'}`}>
            {health.isolated ? 'Container isolated' : 'Local subprocess (dev)'} ·{' '}
            {health.timeout_seconds}s · {health.memory_mb} MB
          </span>
        )}
      </header>

      <div className="row wrap">
        <input
          className="input"
          style={{ maxWidth: 220 }}
          placeholder="new_file.py"
          value={newFileName}
          onChange={(event) => setNewFileName(event.target.value)}
          aria-label="New file name"
        />
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => {
            const name = newFileName.trim();
            if (name && !(name in files)) {
              setFiles((current) => ({ ...current, [name]: '' }));
              setNewFileName('');
            }
          }}
        >
          Add file
        </button>

        <div className="grow" />

        <input
          className="input"
          style={{ maxWidth: 200 }}
          placeholder="save as…"
          value={snippetName}
          onChange={(event) => setSnippetName(event.target.value)}
          aria-label="Workspace name"
        />
        <button type="button" className="btn btn-sm" onClick={() => void save()}>
          Save
        </button>
        <button type="button" className="btn btn-sm" onClick={() => void runReview()} disabled={reviewing}>
          {reviewing ? 'Reviewing…' : 'Review my code'}
        </button>
      </div>

      <CodeEditor files={files} onFilesChange={setFiles} height={430} allowTests />

      {snippets && snippets.length > 0 && (
        <section className="card">
          <h2>Saved workspaces</h2>
          {snippets.map((snippet) => (
            <div key={snippet.id} className="list-row">
              <div>
                <strong className="mono">{snippet.name}</strong>
                <div className="small muted">
                  {Object.keys(snippet.files).length} files · updated{' '}
                  {new Date(snippet.updated_at).toLocaleString()}
                </div>
              </div>
              <div className="row">
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => setFiles(snippet.files)}
                >
                  Load
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={async () => {
                    await execution.deleteSnippet(snippet.name);
                    await refetchSnippets();
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      {review && <ReviewPanel review={review} />}
    </div>
  );
}

function ReviewPanel({ review }: { review: ReviewResponse }) {
  return (
    <section className="card">
      <h2>Code review</h2>
      <Markdown>{review.summary}</Markdown>

      {review.strengths.length > 0 && (
        <div className="alert alert-success">
          <strong>What&apos;s working</strong>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
            {review.strengths.map((strength) => (
              <li key={strength} className="small">
                {strength}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="section-grid" style={{ marginBottom: 'var(--space-4)' }}>
        {Object.entries(review.dimension_scores).map(([dimension, score]) => (
          <MasteryBar
            key={dimension}
            label={dimension.replace(/_/g, ' ')}
            percent={Math.round(score * 100)}
            mastered={score >= 0.95}
            weak={score < 0.6}
          />
        ))}
      </div>

      {review.findings.length === 0 ? (
        <p className="small muted">No findings.</p>
      ) : (
        review.findings.map((finding, index) => (
          <div
            key={index}
            className="check failed"
            style={{
              borderColor:
                finding.severity === 'critical'
                  ? 'var(--danger)'
                  : finding.severity === 'major'
                    ? 'var(--warning)'
                    : 'var(--border)',
              background: 'var(--bg-inset)',
            }}
          >
            <span className={`badge badge-${finding.severity === 'critical' ? 'danger' : 'warning'}`}>
              {finding.severity}
            </span>
            <div>
              <div>
                <span className="mono small faint">
                  {finding.file}
                  {finding.line ? `:${finding.line}` : ''}
                </span>{' '}
                <strong>{finding.message}</strong>
              </div>
              <div className="small muted">{finding.suggestion}</div>
            </div>
          </div>
        ))
      )}
    </section>
  );
}

/* ------------------------------------------------------------ reference */

export function ReferencePage() {
  const [moduleFilter, setModuleFilter] = useState<string>('');
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['reference', moduleFilter],
    queryFn: () => reference.list({ module: moduleFilter || undefined, limit: 200 }),
  });

  if (isLoading) return <Spinner label="Loading the reference" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;

  const modules = Array.from(new Set((data ?? []).map((entry) => entry.module))).sort();

  return (
    <div className="stack">
      <header>
        <h1>Python Reference</h1>
        <p className="muted">
          Signatures, parameters, examples, pitfalls and performance notes. Searchable from the
          bar above.
        </p>
      </header>

      <div className="row wrap">
        <button
          type="button"
          className={`btn btn-sm${moduleFilter === '' ? ' btn-primary' : ''}`}
          onClick={() => setModuleFilter('')}
        >
          All
        </button>
        {modules.map((module) => (
          <button
            key={module}
            type="button"
            className={`btn btn-sm${moduleFilter === module ? ' btn-primary' : ''}`}
            onClick={() => setModuleFilter(module)}
          >
            {module}
          </button>
        ))}
      </div>

      <div className="tile-grid">
        {data?.map((entry) => (
          <Link key={entry.key} to={`/reference/${entry.key}`} className="tile">
            <div className="row-between" style={{ marginBottom: 6 }}>
              <strong className="mono">{entry.key}</strong>
              <span className="badge">{entry.kind}</span>
            </div>
            <div className="small mono faint" style={{ marginBottom: 6 }}>
              {entry.signature}
            </div>
            <p className="small muted" style={{ margin: 0 }}>
              {entry.summary}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function ReferenceEntryPage() {
  const { key = '' } = useParams();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['reference-entry', key],
    queryFn: () => reference.entry(key),
  });

  if (isLoading) return <Spinner label="Loading entry" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;
  if (!data) return null;

  return (
    <div className="stack">
      <nav aria-label="Breadcrumb" className="small muted">
        <Link to="/reference">← Reference</Link>
      </nav>

      <header>
        <h1 className="mono">{data.key}</h1>
        <pre style={{ marginBottom: 'var(--space-3)' }}>
          <code>{data.signature}</code>
        </pre>
        <p className="muted">{data.summary}</p>
      </header>

      {data.description && (
        <section className="card">
          <Markdown>{data.description}</Markdown>
        </section>
      )}

      {data.parameters.length > 0 && (
        <section className="card">
          <h2>Parameters</h2>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Default</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {data.parameters.map((parameter) => (
                <tr key={parameter.name}>
                  <td className="mono">{parameter.name}</td>
                  <td className="mono small">{parameter.type ?? '—'}</td>
                  <td className="mono small">{parameter.default ?? (parameter.required ? '—' : '')}</td>
                  <td className="small">{parameter.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.returns && (
            <p className="small">
              <strong>Returns:</strong> {data.returns}
            </p>
          )}
          {data.raises.length > 0 && (
            <ul className="small" style={{ paddingLeft: 18 }}>
              {data.raises.map((raise) => (
                <li key={raise.type}>
                  <code>{raise.type}</code> — {raise.when}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {data.examples.length > 0 && (
        <section className="card">
          <h2>Examples</h2>
          {data.examples.map((example) => (
            <div key={example.title} style={{ marginBottom: 'var(--space-4)' }}>
              <h3>{example.title}</h3>
              <pre>
                <code>{example.code}</code>
              </pre>
              {example.output && (
                <pre style={{ background: 'var(--bg-elevated)' }}>
                  <code>{example.output}</code>
                </pre>
              )}
            </div>
          ))}
        </section>
      )}

      {data.common_mistakes.length > 0 && (
        <section className="card">
          <h2>Common mistakes</h2>
          {data.common_mistakes.map((mistake) => (
            <div key={mistake.mistake} className="check failed" style={{ background: 'var(--bg-inset)' }}>
              <span className="check-icon" aria-hidden>
                ✗
              </span>
              <div>
                <div>{mistake.mistake}</div>
                <div className="small muted">→ {mistake.fix}</div>
              </div>
            </div>
          ))}
        </section>
      )}

      <div className="section-grid">
        {data.real_world_usage && (
          <div className="section-card">
            <h4>Real-world usage</h4>
            <p>{data.real_world_usage}</p>
          </div>
        )}
        {data.performance_notes && (
          <div className="section-card">
            <h4>Performance</h4>
            <p>{data.performance_notes}</p>
          </div>
        )}
        {data.security_notes && (
          <div className="section-card">
            <h4>Security</h4>
            <p>{data.security_notes}</p>
          </div>
        )}
      </div>

      {(data.related_keys.length > 0 || data.lesson_slugs.length > 0) && (
        <section className="card">
          <h2>See also</h2>
          <div className="row wrap">
            {data.related_keys.map((related) => (
              <Link key={related} to={`/reference/${related}`} className="badge mono">
                {related}
              </Link>
            ))}
            {data.lesson_slugs.map((lesson) => (
              <Link key={lesson} to={`/learn/${lesson}`} className="badge badge-accent">
                {lesson}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- tutor */

export function TutorPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const logRef = useRef<HTMLDivElement>(null);

  const { data: status } = useQuery({ queryKey: ['ai-status'], queryFn: tutor.status });
  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: tutor.conversations,
  });
  const { data: conversation } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => tutor.conversation(conversationId!),
    enabled: Boolean(conversationId),
  });

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [conversation?.messages.length]);

  const start = async (mode: string) => {
    const created = await tutor.start({ mode });
    setConversationId(created.id);
    await queryClient.invalidateQueries({ queryKey: ['conversations'] });
  };

  const send = async () => {
    if (!draft.trim()) return;
    let id = conversationId;
    if (!id) {
      const created = await tutor.start({ mode: 'freeform' });
      id = created.id;
      setConversationId(id);
    }
    setSending(true);
    setSendError(null);
    const message = draft;
    setDraft('');
    try {
      await tutor.send(id, { message });
      await queryClient.invalidateQueries({ queryKey: ['conversation', id] });
    } catch (caught) {
      setSendError(
        caught instanceof ApiError ? caught.message : 'The tutor could not be reached.',
      );
      setDraft(message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="stack">
      <header className="row-between wrap">
        <div>
          <h1 style={{ marginBottom: 4 }}>AI Tutor</h1>
          <p className="muted" style={{ margin: 0 }}>
            Ask about concepts, paste an error, or request a hint. While an exercise is unsolved
            the tutor gives progressively stronger hints — it will not hand over the answer.
          </p>
        </div>
        {status && (
          <span className={`badge ${status.live ? 'badge-success' : 'badge-warning'}`}>
            {status.live ? `${status.model}` : 'Offline mode'} · {status.used_today}/
            {status.daily_limit} today
          </span>
        )}
      </header>

      {!status?.live && (
        <div className="alert alert-warning">
          No model is configured, so the tutor is running its deterministic offline mode: it can
          still explain tracebacks, serve the hint ladder and review your code. Set{' '}
          <code>PYFORGE_ANTHROPIC_API_KEY</code> to enable free-form tutoring.
        </div>
      )}

      <div className="row wrap">
        {(
          [
            ['explain_code', 'Explain code'],
            ['explain_error', 'Explain an error'],
            ['socratic', 'Socratic questions'],
            ['review', 'Review my code'],
            ['generate_tests', 'Generate tests'],
            ['mock_interview', 'Mock interview'],
          ] as const
        ).map(([mode, label]) => (
          <button key={mode} type="button" className="btn btn-sm" onClick={() => void start(mode)}>
            {label}
          </button>
        ))}
      </div>

      <div className="lesson-layout">
        <div className="card" style={{ padding: 0 }}>
          <div className="chat">
            <div className="chat-log" ref={logRef}>
              {!conversation || conversation.messages.length === 0 ? (
                <EmptyState
                  title="Ask anything"
                  hint="Try: “Why does my list change when I modify a copy?”"
                />
              ) : (
                conversation.messages.map((message) => (
                  <div key={message.id} className={`chat-turn ${message.role}`}>
                    <Markdown>{message.content}</Markdown>
                    {message.meta?.withheld_solution === true && (
                      <div className="small faint" style={{ marginTop: 6 }}>
                        Solution withheld — you have an exercise open.
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {sendError && (
              <div className="alert alert-error" style={{ margin: 'var(--space-3)' }}>
                {sendError}
              </div>
            )}

            <div className="chat-composer">
              <label htmlFor="tutor-input" className="visually-hidden">
                Message the tutor
              </label>
              <textarea
                id="tutor-input"
                className="textarea"
                style={{ minHeight: 60 }}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) void send();
                }}
                placeholder="Ask a question, or paste a traceback…  (⌘↵ to send)"
              />
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void send()}
                disabled={sending || !draft.trim()}
              >
                {sending ? '…' : 'Send'}
              </button>
            </div>
          </div>
        </div>

        <aside className="lesson-aside">
          <div className="card">
            <h2>Conversations</h2>
            {!conversations || conversations.length === 0 ? (
              <p className="small muted">Nothing yet.</p>
            ) : (
              conversations.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`nav-link${item.id === conversationId ? ' active' : ''}`}
                  style={{ width: '100%', textAlign: 'left', border: 'none', cursor: 'pointer' }}
                  onClick={() => setConversationId(item.id)}
                >
                  {item.title}
                </button>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- progress */

export function ProgressPage() {
  const { data: mastery, isLoading, error, refetch } = useQuery({
    queryKey: ['mastery'],
    queryFn: progress.mastery,
  });
  const { data: certifications } = useQuery({
    queryKey: ['certifications'],
    queryFn: progress.certifications,
  });
  const { data: achievements } = useQuery({
    queryKey: ['achievements'],
    queryFn: progress.achievements,
  });

  if (isLoading) return <Spinner label="Loading your progress" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;

  const byCategory = new Map<string, MasteryItem[]>();
  for (const concept of mastery?.concepts ?? []) {
    const bucket = byCategory.get(concept.category) ?? [];
    bucket.push(concept);
    byCategory.set(concept.category, bucket);
  }

  return (
    <div className="stack">
      <header>
        <h1>Progress</h1>
        <p className="muted">
          Mastery is an estimate of what you can do unaided, not a count of pages viewed. It rises
          with unassisted success, is discounted by hints, and decays without practice.
        </p>
      </header>

      <section className="card">
        <div className="row-between">
          <h2 style={{ margin: 0 }}>Overall mastery</h2>
          <strong style={{ fontSize: '1.4rem' }}>
            {Math.round((mastery?.overall ?? 0) * 100)}%
          </strong>
        </div>
        <div className="meter" style={{ marginTop: 10 }}>
          <div className="meter-fill" style={{ width: `${(mastery?.overall ?? 0) * 100}%` }} />
        </div>
        <p className="small muted" style={{ marginTop: 8, marginBottom: 0 }}>
          {mastery?.mastered_count ?? 0} concepts mastered.
        </p>
      </section>

      {mastery && mastery.concepts.length === 0 && (
        <EmptyState
          title="No mastery data yet"
          hint="Submit an exercise and this page fills in immediately."
        />
      )}

      {[...byCategory.entries()].map(([category, concepts]) => (
        <section key={category} className="card">
          <h2 style={{ textTransform: 'capitalize' }}>{category.replace(/-/g, ' ')}</h2>
          {concepts.map((concept) => (
            <div key={concept.concept_slug}>
              <MasteryBar
                label={concept.concept_name}
                percent={concept.percent}
                mastered={concept.is_mastered}
                weak={concept.score < 0.5}
              />
              <div className="small faint" style={{ marginTop: -8, marginBottom: 12 }}>
                {concept.attempts} attempts · {Math.round(concept.accuracy * 100)}% accuracy ·{' '}
                {concept.band.replace(/_/g, ' ')}
                {concept.top_misconceptions.length > 0 &&
                  ` · struggling with: ${concept.top_misconceptions.join(', ')}`}
              </div>
            </div>
          ))}
        </section>
      ))}

      <section className="card">
        <h2>Certifications</h2>
        <p className="small muted">
          Each unlocks on demonstrated mastery — never on lessons completed or time spent.
        </p>
        {certifications?.map((certification) => (
          <div key={certification.level} className="list-row" style={{ alignItems: 'flex-start' }}>
            <div style={{ minWidth: 0 }}>
              <div className="row" style={{ gap: 8 }}>
                <strong>{certification.title}</strong>
                {certification.earned && <span className="badge badge-success">Earned</span>}
                {!certification.earned && certification.eligible && (
                  <span className="badge badge-accent">Ready to claim</span>
                )}
              </div>
              <div className="small muted">{certification.description}</div>
              {!certification.earned && certification.unmet_requirements.length > 0 && (
                <ul className="small faint" style={{ paddingLeft: 18, marginTop: 6 }}>
                  {certification.unmet_requirements.slice(0, 4).map((requirement) => (
                    <li key={requirement}>{requirement}</li>
                  ))}
                </ul>
              )}
              {certification.certificate_code && (
                <div className="small mono faint">{certification.certificate_code}</div>
              )}
            </div>
            <div style={{ minWidth: 90, textAlign: 'right' }}>
              <strong>{Math.round(certification.progress * 100)}%</strong>
              {certification.eligible && !certification.earned && (
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  style={{ marginTop: 6 }}
                  onClick={async () => {
                    await progress.claimCertification(certification.level);
                    window.location.reload();
                  }}
                >
                  Claim
                </button>
              )}
            </div>
          </div>
        ))}
      </section>

      <section className="card">
        <h2>Achievements</h2>
        <div className="tile-grid">
          {achievements?.map((achievement) => (
            <div
              key={achievement.slug}
              className="section-card"
              style={{ opacity: achievement.earned ? 1 : 0.5 }}
            >
              <div className="row-between">
                <strong>{achievement.name}</strong>
                <span className={`badge${achievement.earned ? ' badge-success' : ''}`}>
                  {achievement.tier}
                </span>
              </div>
              <p className="small muted" style={{ marginTop: 6, marginBottom: 0 }}>
                {achievement.description}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/* ------------------------------------------------------------ interview */

export function InterviewPage() {
  const [track, setTrack] = useState('');
  const [answers, setAnswers] = useState<Record<string, { chosen: number; correct: boolean; explanation: string }>>(
    {},
  );

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['interview', track],
    queryFn: () => interview.questions({ track: track || undefined, limit: 30 }),
  });

  if (isLoading) return <Spinner label="Loading questions" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;

  const answer = async (slug: string, index: number) => {
    const result = await interview.answer(slug, index);
    setAnswers((current) => ({
      ...current,
      [slug]: { chosen: index, correct: result.correct, explanation: result.explanation },
    }));
  };

  return (
    <div className="stack">
      <header>
        <h1>Interview Preparation</h1>
        <p className="muted">
          Questions drawn from real interviews. Every answer comes with the reasoning, because
          the reasoning is what gets asked about next.
        </p>
      </header>

      <div className="row wrap">
        {['', 'python-developer', 'backend', 'automation', 'sdet', 'test-architect'].map((value) => (
          <button
            key={value || 'all'}
            type="button"
            className={`btn btn-sm${track === value ? ' btn-primary' : ''}`}
            onClick={() => setTrack(value)}
          >
            {value === '' ? 'All tracks' : value.replace(/-/g, ' ')}
          </button>
        ))}
      </div>

      {data?.map((question) => {
        const answered = answers[question.slug];
        return (
          <section key={question.slug} className="card">
            <div className="row wrap" style={{ marginBottom: 8 }}>
              <span className="badge">{question.category}</span>
              <span className="badge">{question.level}</span>
            </div>
            <h2 style={{ fontSize: '1.05rem' }}>{question.question}</h2>
            {question.code_snippet && (
              <pre>
                <code>{question.code_snippet}</code>
              </pre>
            )}
            <div className="stack">
              {question.options.map((option, index) => {
                const isChosen = answered?.chosen === index;
                return (
                  <button
                    key={option}
                    type="button"
                    className="list-row"
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      cursor: answered ? 'default' : 'pointer',
                      borderColor: isChosen
                        ? answered.correct
                          ? 'var(--success)'
                          : 'var(--danger)'
                        : 'var(--border)',
                    }}
                    disabled={Boolean(answered)}
                    onClick={() => void answer(question.slug, index)}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
            {answered && (
              <div className={`alert ${answered.correct ? 'alert-success' : 'alert-warning'}`} style={{ marginTop: 12 }}>
                <strong>{answered.correct ? 'Correct.' : 'Not quite.'}</strong>{' '}
                {answered.explanation}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------- settings */

export function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name ?? '');
  const [goal, setGoal] = useState(user?.goal ?? '');
  const [saved, setSaved] = useState(false);

  const { data: health } = useQuery({ queryKey: ['exec-health'], queryFn: execution.health });

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    await auth.updateProfile({ display_name: displayName, goal });
    await refreshUser();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="stack" style={{ maxWidth: 640 }}>
      <h1>Settings</h1>

      {saved && <div className="alert alert-success">Saved.</div>}

      <form className="card" onSubmit={save}>
        <h2>Profile</h2>
        <div className="field">
          <label htmlFor="settings-name">Display name</label>
          <input
            id="settings-name"
            className="input"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="settings-goal">Learning goal</label>
          <input
            id="settings-goal"
            className="input"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="e.g. build our internal reporting API"
          />
        </div>
        <button type="submit" className="btn btn-primary">
          Save
        </button>
      </form>

      <section className="card">
        <h2>Execution engine</h2>
        {health ? (
          <>
            <div className="row-between small">
              <span>Backend</span>
              <span className="mono">{health.backend}</span>
            </div>
            <div className="row-between small">
              <span>Container isolated</span>
              <StatusBadge status={health.isolated ? 'passed' : 'failed'} />
            </div>
            <div className="row-between small">
              <span>Time limit</span>
              <span className="mono">{health.timeout_seconds}s</span>
            </div>
            <div className="row-between small">
              <span>Memory limit</span>
              <span className="mono">{health.memory_mb} MB</span>
            </div>
            <div className="row-between small">
              <span>Max files per run</span>
              <span className="mono">{health.max_files}</span>
            </div>
          </>
        ) : (
          <Spinner />
        )}
      </section>

      <section className="card">
        <h2>Account</h2>
        <div className="row-between small">
          <span>Email</span>
          <span className="mono">{user?.email}</span>
        </div>
        <div className="row-between small">
          <span>Total coding time</span>
          <span>{Math.round((user?.total_coding_seconds ?? 0) / 3600)}h</span>
        </div>
      </section>
    </div>
  );
}
