/** The project academy: catalogue, brief, IDE and rubric review. */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { projects } from '@/api/endpoints';
import type { ProjectSubmission } from '@/api/types';
import { CodeEditor } from '@/components/CodeEditor';
import { ErrorNotice, Markdown, Spinner, StatusBadge } from '@/components/ui';

const GUIDANCE_LABEL: Record<string, string> = {
  fully_guided: 'Fully guided',
  partially_guided: 'Partially guided',
  requirements_only: 'Requirements only',
  independent: 'Independent',
};

export function ProjectsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['projects'],
    queryFn: projects.list,
  });

  if (isLoading) return <Spinner label="Loading the project academy" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;

  return (
    <div className="stack">
      <header>
        <h1>Project Academy</h1>
        <p className="muted">
          Scaffolding fades as you progress: the first project spells out every step, the last
          hands you a requirement document and nothing else.
        </p>
      </header>

      <div className="tile-grid">
        {data?.map((project) => (
          <Link key={project.slug} to={`/projects/${project.slug}`} className="tile">
            <div className="row-between" style={{ marginBottom: 8 }}>
              <strong>{project.title}</strong>
              <StatusBadge status={project.status} />
            </div>
            <p className="small muted">{project.tagline}</p>
            <div className="row wrap" style={{ marginTop: 10 }}>
              <span className="badge">{project.level}</span>
              <span className="badge">{GUIDANCE_LABEL[project.guidance] ?? project.guidance}</span>
              <span className="badge">~{project.estimated_hours}h</span>
              {project.is_capstone && <span className="badge badge-accent">Capstone</span>}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function ProjectPage() {
  const { slug = '' } = useParams();
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<Record<string, string>>({});
  const [newFileName, setNewFileName] = useState('');
  const [submission, setSubmission] = useState<ProjectSubmission | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: project, isLoading, error, refetch } = useQuery({
    queryKey: ['project', slug],
    queryFn: () => projects.detail(slug),
  });

  useEffect(() => {
    if (!project) return;
    const workspace = project.workspace?.files;
    setFiles(
      workspace && Object.keys(workspace).length > 0
        ? workspace
        : Object.keys(project.starter_files).length > 0
          ? project.starter_files
          : { 'main.py': '', 'README.md': `# ${project.title}\n` },
    );
  }, [project]);

  // Autosave the workspace.
  useEffect(() => {
    if (!project || Object.keys(files).length === 0) return;
    const timer = setTimeout(() => {
      void projects.saveWorkspace(project.slug, { files }).catch(() => undefined);
    }, 3000);
    return () => clearTimeout(timer);
  }, [files, project]);

  if (isLoading) return <Spinner label="Loading project" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;
  if (!project) return null;

  const addFile = () => {
    const name = newFileName.trim();
    if (!name || name in files) return;
    setFiles((current) => ({ ...current, [name]: '' }));
    setNewFileName('');
  };

  const submit = async () => {
    setBusy(true);
    setActionError(null);
    try {
      setSubmission(await projects.submit(project.slug, files));
      await queryClient.invalidateQueries({ queryKey: ['project', slug] });
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    } catch (caught) {
      setActionError(
        caught instanceof ApiError ? caught.message : 'Submission failed. Please try again.',
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 'var(--space-5)' }} className="stack">
      <nav aria-label="Breadcrumb" className="small muted">
        <Link to="/projects">← Project Academy</Link>
      </nav>

      <header className="row-between wrap">
        <div>
          <h1 style={{ marginBottom: 4 }}>{project.title}</h1>
          <p className="muted" style={{ marginBottom: 8 }}>
            {project.tagline}
          </p>
          <div className="row wrap">
            <span className="badge">{project.level}</span>
            <span className="badge">{GUIDANCE_LABEL[project.guidance] ?? project.guidance}</span>
            <span className="badge">~{project.estimated_hours}h</span>
            <span className="badge badge-accent">{project.xp_reward} XP</span>
            <StatusBadge status={project.status} />
          </div>
        </div>
      </header>

      {actionError && (
        <div className="alert alert-error" role="alert">
          {actionError}
        </div>
      )}

      <div className="lesson-layout">
        <div className="stack">
          <article className="card">
            <Markdown>{project.requirements}</Markdown>
          </article>

          {project.architecture_notes && (
            <section className="card">
              <h2>Design notes</h2>
              <Markdown>{project.architecture_notes}</Markdown>
            </section>
          )}

          {project.suggested_structure && (
            <section className="card">
              <h2>Suggested structure</h2>
              <pre>
                <code>{project.suggested_structure}</code>
              </pre>
            </section>
          )}

          {project.milestones.length > 0 && (
            <section className="card">
              <h2>Milestones</h2>
              <ol style={{ paddingLeft: 20, margin: 0 }}>
                {project.milestones.map((milestone) => (
                  <li key={milestone.key} style={{ marginBottom: 10 }}>
                    <strong>{milestone.title}</strong>
                    <div className="small muted">{milestone.detail}</div>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className="card">
            <h2>How this is assessed</h2>
            <table>
              <thead>
                <tr>
                  <th>Criterion</th>
                  <th>Weight</th>
                  <th>What we look for</th>
                </tr>
              </thead>
              <tbody>
                {project.rubric.map((criterion) => (
                  <tr key={criterion.key}>
                    <td>{criterion.label}</td>
                    <td>{criterion.weight}</td>
                    <td className="small muted">{criterion.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {submission && (
            <section
              className="card"
              style={{
                borderColor:
                  submission.verdict === 'passed' ? 'var(--success)' : 'var(--warning)',
              }}
              aria-live="polite"
            >
              <div className="row-between">
                <h2 style={{ margin: 0 }}>Engineering review</h2>
                <StatusBadge status={submission.verdict} />
              </div>
              <p className="small muted">
                Acceptance tests: {submission.tests_passed}/{submission.tests_total} ·{' '}
                Overall: {Math.round(submission.overall_score * 100)}%
                {submission.xp_awarded > 0 && ` · +${submission.xp_awarded} XP`}
              </p>
              <Markdown>{submission.review_markdown}</Markdown>
              {submission.stderr && (
                <>
                  <h3>Test output</h3>
                  <pre>
                    <code>{submission.stderr.slice(0, 4000)}</code>
                  </pre>
                </>
              )}
            </section>
          )}
        </div>

        <aside className="lesson-aside stack">
          <div className="row">
            <input
              className="input"
              placeholder="new/file.py"
              value={newFileName}
              onChange={(event) => setNewFileName(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && addFile()}
              aria-label="New file name"
            />
            <button type="button" className="btn btn-sm" onClick={addFile}>
              Add file
            </button>
          </div>

          <CodeEditor
            files={files}
            onFilesChange={setFiles}
            entrypoint={project.workspace?.entrypoint ?? 'main.py'}
            height={480}
            allowTests
            actions={
              <button
                type="button"
                className="btn btn-success btn-sm"
                onClick={() => void submit()}
                disabled={busy}
              >
                {busy ? 'Evaluating…' : 'Submit project'}
              </button>
            }
          />

          <p className="small muted">
            Files autosave. Submitting runs the acceptance tests in the sandbox and scores your
            build against the rubric.
          </p>
        </aside>
      </div>
    </div>
  );
}
