/** The exercise workspace: prompt, editor, hints, submission and feedback. */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { exercises } from '@/api/endpoints';
import type { Hint, Remediation, SubmissionResponse } from '@/api/types';
import { CodeEditor } from '@/components/CodeEditor';
import {
  CheckList,
  EmptyState,
  ErrorNotice,
  Markdown,
  MasteryDeltas,
  Spinner,
  StatusBadge,
} from '@/components/ui';

export function PracticePage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['challenges'],
    queryFn: () => exercises.challenges(),
  });

  if (isLoading) return <Spinner label="Loading exercises" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;

  return (
    <div className="stack">
      <header>
        <h1>Practice</h1>
        <p className="muted">
          Exercises live inside their lessons. Standalone challenges are listed here.
        </p>
      </header>

      {!data || data.length === 0 ? (
        <EmptyState
          title="No standalone challenges yet"
          hint="Open a lesson from Learn — every lesson ends in exercises."
        />
      ) : (
        <div className="tile-grid">
          {data.map((challenge) => (
            <Link key={challenge.slug} to={`/practice/${challenge.slug}`} className="tile">
              <div className="row-between" style={{ marginBottom: 8 }}>
                <strong>{challenge.title}</strong>
                <StatusBadge status={challenge.status} />
              </div>
              <p className="small muted">{challenge.prompt.slice(0, 140)}…</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function ExercisePage() {
  const { slug = '' } = useParams();
  const queryClient = useQueryClient();

  const [files, setFiles] = useState<Record<string, string>>({});
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [hints, setHints] = useState<Hint[]>([]);
  const [solution, setSolution] = useState<{ files: Record<string, string>; explanation: string } | null>(
    null,
  );
  const [submission, setSubmission] = useState<SubmissionResponse | null>(null);
  const [remediation, setRemediation] = useState<Remediation | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const startedAt = useRef(Date.now());

  const { data: exercise, isLoading, error, refetch } = useQuery({
    queryKey: ['exercise', slug],
    queryFn: () => exercises.detail(slug),
  });

  useEffect(() => {
    if (!exercise) return;
    setFiles(
      Object.keys(exercise.starter_files).length > 0
        ? exercise.starter_files
        : { 'main.py': '' },
    );
    startedAt.current = Date.now();
  }, [exercise]);

  // Restore hints the learner already unlocked in a previous session — the
  // penalty was already paid, so hiding them would be a second charge for the
  // same help.
  useEffect(() => {
    if (!exercise || exercise.hints_revealed === 0) return;
    let cancelled = false;
    void (async () => {
      const restored: Hint[] = [];
      for (let level = 1; level <= exercise.hints_revealed; level += 1) {
        try {
          restored.push(await exercises.hint(exercise.slug, level));
        } catch {
          break;
        }
      }
      if (!cancelled) setHints(restored);
    })();
    return () => {
      cancelled = true;
    };
  }, [exercise]);

  const isQuiz = exercise?.grader === 'multiple_choice';
  // Restored hints and the server's count describe the same reveals, so take the
  // greater of the two rather than adding them.
  const hintsShown = Math.max(hints.length, exercise?.hints_revealed ?? 0);
  const nextHintLevel = hintsShown + 1;
  const hintsRemaining = useMemo(
    () => Math.max(0, (exercise?.hint_count ?? 0) - hintsShown),
    [exercise, hintsShown],
  );

  if (isLoading) return <Spinner label="Loading exercise" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;
  if (!exercise) return null;

  const revealHint = async () => {
    setActionError(null);
    try {
      const hint = await exercises.hint(exercise.slug, nextHintLevel);
      setHints((current) => [...current, hint]);
    } catch (caught) {
      setActionError(caught instanceof ApiError ? caught.message : 'Could not load a hint.');
    }
  };

  const revealSolution = async () => {
    setActionError(null);
    try {
      setSolution(await exercises.solution(exercise.slug));
    } catch (caught) {
      setActionError(
        caught instanceof ApiError
          ? caught.message
          : 'The solution is not available yet.',
      );
    }
  };

  const submit = async () => {
    setSubmitting(true);
    setActionError(null);
    try {
      const result = await exercises.submit(
        exercise.slug,
        {
          files,
          selected_index: isQuiz ? selectedOption : null,
          time_spent_seconds: Math.round((Date.now() - startedAt.current) / 1000),
        },
        exercise.execution_plan,
      );
      setSubmission(result);
      setRemediation(await exercises.remediation(exercise.slug).catch(() => null));
      await queryClient.invalidateQueries({ queryKey: ['exercise', slug] });
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    } catch (caught) {
      setActionError(
        caught instanceof ApiError ? caught.message : 'Submission failed. Please try again.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="stack">
      {exercise.lesson_slug && (
        <nav aria-label="Breadcrumb" className="small muted">
          <Link to={`/learn/${exercise.lesson_slug}`}>← Back to the lesson</Link>
        </nav>
      )}

      <header className="row-between wrap">
        <div>
          <h1 style={{ marginBottom: 4 }}>{exercise.title}</h1>
          <div className="row wrap">
            <span className="badge">{exercise.kind.replace(/_/g, ' ')}</span>
            <span className="badge">{exercise.estimated_minutes} min</span>
            <span className="badge badge-accent">{exercise.xp_reward} XP</span>
            <StatusBadge status={exercise.status} />
            {exercise.attempts > 0 && (
              <span className="small muted">
                {exercise.attempts} attempt{exercise.attempts === 1 ? '' : 's'}
              </span>
            )}
          </div>
        </div>
      </header>

      {actionError && (
        <div className="alert alert-warning" role="alert">
          {actionError}
        </div>
      )}

      <div className="lesson-layout">
        <div className="stack">
          <article className="card">
            <Markdown>{exercise.prompt}</Markdown>
          </article>

          {hints.map((hint) => (
            <div key={hint.level} className="hint">
              <div className="hint-level">
                Hint {hint.level} of {exercise.hint_count}
              </div>
              <Markdown>{hint.text}</Markdown>
            </div>
          ))}

          {remediation && remediation.stage !== 'resolved' && (
            <section className="card" style={{ borderColor: 'var(--warning)' }}>
              <h2>Let&apos;s change approach</h2>
              <p>{remediation.message}</p>
              {remediation.misconception_label && (
                <p className="small">
                  <strong>Pattern spotted:</strong> {remediation.misconception_label}
                </p>
              )}
              {remediation.explanation && <Markdown>{remediation.explanation}</Markdown>}
              {remediation.next_exercise_slug && (
                <Link className="btn btn-primary" to={`/practice/${remediation.next_exercise_slug}`}>
                  Try the easier step →
                </Link>
              )}
            </section>
          )}

          {solution && (
            <section className="card" style={{ borderColor: 'var(--info)' }}>
              <h2>Reference solution</h2>
              {Object.entries(solution.files).map(([name, content]) => (
                <div key={name}>
                  <div className="small faint mono">{name}</div>
                  <pre>
                    <code>{content}</code>
                  </pre>
                </div>
              ))}
              <Markdown>{solution.explanation}</Markdown>
            </section>
          )}

          {submission && (
            <section
              className="card"
              style={{
                borderColor:
                  submission.status === 'passed' ? 'var(--success)' : 'var(--border-strong)',
              }}
              aria-live="polite"
            >
              <div className="row-between" style={{ marginBottom: 'var(--space-3)' }}>
                <h2 style={{ margin: 0 }}>
                  Attempt {submission.attempt_number} · {Math.round(submission.score * 100)}%
                </h2>
                <StatusBadge status={submission.status} />
              </div>

              <Markdown>{submission.feedback}</Markdown>
              <CheckList checks={submission.checks} />

              {submission.xp_awarded > 0 && (
                <p className="small" style={{ color: 'var(--success)' }}>
                  +{submission.xp_awarded} XP
                </p>
              )}
              {submission.newly_earned_achievements.length > 0 && (
                <div className="row wrap">
                  {submission.newly_earned_achievements.map((badge) => (
                    <span key={badge} className="badge badge-success">
                      Achievement unlocked: {badge}
                    </span>
                  ))}
                </div>
              )}
              <MasteryDeltas deltas={submission.mastery_deltas} />
            </section>
          )}
        </div>

        <aside className="lesson-aside stack">
          {isQuiz ? (
            <fieldset className="card" style={{ border: '1px solid var(--border)' }}>
              <legend className="small faint">Choose one</legend>
              {(exercise.options ?? []).map((option, index) => (
                <label
                  key={option}
                  className="row"
                  style={{ alignItems: 'flex-start', marginBottom: 'var(--space-3)' }}
                >
                  <input
                    type="radio"
                    name="quiz-option"
                    checked={selectedOption === index}
                    onChange={() => setSelectedOption(index)}
                    style={{ marginTop: 5 }}
                  />
                  <span>{option}</span>
                </label>
              ))}
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void submit()}
                disabled={selectedOption === null || submitting}
              >
                Submit answer
              </button>
            </fieldset>
          ) : (
            <CodeEditor
              files={files}
              onFilesChange={setFiles}
              exerciseSlug={exercise.slug}
              height={400}
              allowTests={exercise.grader === 'pytest'}
              onReset={() => setFiles(exercise.starter_files)}
              actions={
                <>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => void revealHint()}
                    disabled={hintsRemaining === 0}
                    title={
                      hintsRemaining === 0
                        ? 'No hints left'
                        : `${hintsRemaining} hint${hintsRemaining === 1 ? '' : 's'} remaining`
                    }
                  >
                    Hint ({hintsRemaining})
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => void revealSolution()}>
                    Solution
                  </button>
                  <button
                    type="button"
                    className="btn btn-success btn-sm"
                    onClick={() => void submit()}
                    disabled={submitting}
                  >
                    {submitting ? 'Grading…' : 'Submit'}
                  </button>
                </>
              }
            />
          )}

          <div className="card card-tight small muted">
            <strong>How this is graded</strong>
            <p style={{ margin: '6px 0 0' }}>
              {exercise.grader === 'pytest'
                ? 'A hidden pytest suite runs against your code in an isolated sandbox. Your score is the fraction of tests that pass.'
                : exercise.grader === 'stdout_match'
                  ? 'Your program is run and its output compared with the expected output, ignoring only trailing whitespace.'
                  : exercise.grader === 'static_assert'
                    ? 'Your code is parsed and checked structurally — a construct mentioned in a comment does not count.'
                    : 'Your answer is compared with the key, and the reasoning is explained either way.'}
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
