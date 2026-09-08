/** Course browser and the lesson page. */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { curriculum } from '@/api/endpoints';
import { CodeEditor } from '@/components/CodeEditor';
import { EmptyState, ErrorNotice, Markdown, Spinner, StatusBadge } from '@/components/ui';

const SECTION_LABELS: Array<[string, string]> = [
  ['what_is_it', 'What is it?'],
  ['why_it_exists', 'Why does it exist?'],
  ['how_it_works', 'How does it work?'],
  ['when_to_use', 'When should I use it?'],
  ['when_not_to_use', 'When should I NOT use it?'],
  ['common_mistakes', 'Common mistakes'],
  ['real_world', 'In real projects'],
  ['alternatives', 'Alternatives'],
  ['performance', 'Performance'],
  ['security', 'Security'],
];

export function LearnPage() {
  const { data: courses, isLoading, error, refetch } = useQuery({
    queryKey: ['courses'],
    queryFn: curriculum.courses,
  });
  const primary = courses?.[0];

  const { data: course } = useQuery({
    queryKey: ['course', primary?.slug],
    queryFn: () => curriculum.course(primary!.slug),
    enabled: Boolean(primary),
  });

  if (isLoading) return <Spinner label="Loading the curriculum" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;
  if (!primary) return <EmptyState title="No courses are loaded" hint="Run `make seed`." />;

  return (
    <div className="stack">
      <header>
        <h1>{primary.title}</h1>
        <p className="muted">{primary.subtitle}</p>
        <div className="row wrap small muted">
          <span>{primary.module_count} modules</span>
          <span>·</span>
          <span>{primary.lesson_count} lessons</span>
          <span>·</span>
          <span>~{primary.estimated_hours} hours</span>
        </div>
      </header>

      {primary.outcomes.length > 0 && (
        <section className="card">
          <h2>By the end you will be able to</h2>
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            {primary.outcomes.map((outcome) => (
              <li key={outcome}>{outcome}</li>
            ))}
          </ul>
        </section>
      )}

      {course?.modules.map((module) => (
        <section key={module.slug} className="card">
          <div className="row-between" style={{ marginBottom: 'var(--space-3)' }}>
            <div>
              <h2 style={{ marginBottom: 4 }}>{module.title}</h2>
              <p className="small muted" style={{ margin: 0 }}>
                {module.summary}
              </p>
            </div>
            <span className="badge">{module.level}</span>
          </div>

          {module.lessons.map((lesson) => (
            <Link key={lesson.slug} to={`/learn/${lesson.slug}`} className="list-row">
              <div style={{ minWidth: 0 }}>
                <strong>{lesson.title}</strong>
                <div className="small muted">{lesson.summary}</div>
              </div>
              <div className="row" style={{ gap: 8, flexShrink: 0 }}>
                <span className="small faint">{lesson.estimated_minutes}m</span>
                {lesson.exercise_count > 0 && (
                  <span className="badge">{lesson.exercise_count} exercises</span>
                )}
                <StatusBadge status={lesson.status} />
              </div>
            </Link>
          ))}
        </section>
      ))}
    </div>
  );
}

export function LessonPage() {
  const { slug = '' } = useParams();
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<Record<string, string>>({});

  const { data: lesson, isLoading, error, refetch } = useQuery({
    queryKey: ['lesson', slug],
    queryFn: () => curriculum.lesson(slug),
  });

  // Record the view once per lesson, and restore any saved scratch code.
  useEffect(() => {
    if (!slug) return;
    void curriculum.viewLesson(slug).catch(() => undefined);
  }, [slug]);

  useEffect(() => {
    if (!lesson) return;
    const saved = lesson.progress?.scratch_files;
    setFiles(
      saved && Object.keys(saved).length > 0 ? saved : { 'main.py': lesson.starter_code },
    );
  }, [lesson]);

  // Autosave scratch code, debounced so typing does not hammer the API.
  useEffect(() => {
    if (!lesson || Object.keys(files).length === 0) return;
    const timer = setTimeout(() => {
      void curriculum.saveScratch(lesson.slug, files).catch(() => undefined);
    }, 2500);
    return () => clearTimeout(timer);
  }, [files, lesson]);

  const sections = useMemo(
    () => SECTION_LABELS.filter(([key]) => lesson?.sections?.[key]),
    [lesson],
  );

  if (isLoading) return <Spinner label="Loading lesson" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;
  if (!lesson) return null;

  const complete = async () => {
    await curriculum.completeLesson(lesson.slug);
    await queryClient.invalidateQueries({ queryKey: ['lesson', slug] });
    await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };

  return (
    <div className="stack">
      <nav aria-label="Breadcrumb" className="small muted">
        <Link to="/learn">Learn</Link> / {lesson.module_title}
      </nav>

      <header className="row-between wrap">
        <div>
          <h1 style={{ marginBottom: 4 }}>{lesson.title}</h1>
          <p className="muted" style={{ marginBottom: 8 }}>
            {lesson.summary}
          </p>
          <div className="row wrap">
            <span className="badge">{lesson.level}</span>
            <span className="badge">{lesson.estimated_minutes} min</span>
            {lesson.concepts.map((concept) => (
              <span key={concept.slug} className="badge badge-accent">
                {concept.name}
              </span>
            ))}
          </div>
        </div>
      </header>

      <div className="lesson-layout">
        <div className="lesson-body stack">
          <article className="card">
            <Markdown>{lesson.body}</Markdown>
          </article>

          {lesson.examples.length > 0 && (
            <section className="card">
              <h2>Worked examples</h2>
              {lesson.examples.map((example) => (
                <div key={example.title} style={{ marginBottom: 'var(--space-5)' }}>
                  <h3>{example.title}</h3>
                  <pre>
                    <code>{example.code}</code>
                  </pre>
                  {example.output && (
                    <>
                      <div className="small faint" style={{ margin: '6px 0 4px' }}>
                        Output
                      </div>
                      <pre style={{ background: 'var(--bg-elevated)' }}>
                        <code>{example.output}</code>
                      </pre>
                    </>
                  )}
                  {example.explanation && <p className="small muted">{example.explanation}</p>}
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => setFiles({ 'main.py': example.code })}
                  >
                    Load into the editor
                  </button>
                </div>
              ))}
            </section>
          )}

          <section className="card">
            <h2>The ten questions</h2>
            <p className="small muted">
              Every lesson on this platform answers all ten. If one is thin, the lesson is not
              finished.
            </p>
            <div className="section-grid">
              {sections.map(([key, label]) => (
                <div key={key} className="section-card">
                  <h4>{label}</h4>
                  <p>{lesson.sections[key]}</p>
                </div>
              ))}
            </div>
          </section>

          {lesson.exercises.length > 0 && (
            <section className="card">
              <h2>Practice</h2>
              {lesson.exercises.map((exercise) => (
                <Link key={exercise.slug} to={`/practice/${exercise.slug}`} className="list-row">
                  <div>
                    <strong>{exercise.title}</strong>
                    <div className="small muted">
                      {exercise.kind.replace(/_/g, ' ')} · {exercise.estimated_minutes} min ·{' '}
                      {exercise.xp_reward} XP
                    </div>
                  </div>
                  <StatusBadge status={exercise.status} />
                </Link>
              ))}
            </section>
          )}

          {lesson.reference_keys.length > 0 && (
            <section className="card">
              <h2>Reference</h2>
              <div className="row wrap">
                {lesson.reference_keys.map((key) => (
                  <Link key={key} to={`/reference/${key}`} className="badge mono">
                    {key}
                  </Link>
                ))}
              </div>
            </section>
          )}

          <nav className="row-between" aria-label="Lesson navigation">
            {lesson.previous_lesson_slug ? (
              <Link className="btn" to={`/learn/${lesson.previous_lesson_slug}`}>
                ← Previous
              </Link>
            ) : (
              <span />
            )}
            <button type="button" className="btn btn-success" onClick={() => void complete()}>
              Mark complete
            </button>
            {lesson.next_lesson_slug ? (
              <Link className="btn btn-primary" to={`/learn/${lesson.next_lesson_slug}`}>
                Next →
              </Link>
            ) : (
              <span />
            )}
          </nav>
        </div>

        <aside className="lesson-aside">
          <div className="small faint" style={{ marginBottom: 6 }}>
            Scratch editor — experiment freely, it autosaves
          </div>
          <CodeEditor
            files={files}
            onFilesChange={setFiles}
            lessonSlug={lesson.slug}
            height={420}
            onReset={() => setFiles({ 'main.py': lesson.starter_code })}
          />
        </aside>
      </div>
    </div>
  );
}
