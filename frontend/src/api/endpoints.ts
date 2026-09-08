/** Endpoint-shaped wrappers around the HTTP client. */

import { api } from './client';
import * as pyodide from '@/execution/runner';
import type {
  Achievement,
  AIStatus,
  AuthResponse,
  CertificationStatus,
  ChallengeSummary,
  ConversationDetail,
  CourseDetail,
  CourseSummary,
  Dashboard,
  ExecuteResponse,
  ExecutionHealth,
  ExecutionPlan,
  ExerciseDetail,
  Hint,
  LessonDetail,
  LessonProgress,
  MasteryOverview,
  ProjectDetail,
  ProjectSubmission,
  ProjectSummary,
  QuizAnswer,
  QuizQuestion,
  Recommendation,
  ReferenceDetail,
  ReferenceSummary,
  Remediation,
  ReviewResponse,
  SearchResponse,
  SubmissionResponse,
  User,
} from './types';

export const auth = {
  register: (body: {
    email: string;
    password: string;
    display_name: string;
    declared_level?: string;
    goal?: string;
  }) => api.post<AuthResponse>('/api/auth/register', body),
  login: (body: { email: string; password: string }) =>
    api.post<AuthResponse>('/api/auth/login', body),
  me: () => api.get<User>('/api/auth/me'),
  updateProfile: (body: Partial<Pick<User, 'display_name' | 'goal'>> & Record<string, unknown>) =>
    api.patch<User>('/api/auth/me', body),
};

export const curriculum = {
  courses: () => api.get<CourseSummary[]>('/api/courses'),
  course: (slug: string) => api.get<CourseDetail>(`/api/courses/${slug}`),
  lesson: (slug: string) => api.get<LessonDetail>(`/api/lessons/${slug}`),
  viewLesson: (slug: string) => api.post<LessonProgress>(`/api/lessons/${slug}/view`),
  completeLesson: (slug: string) => api.post<LessonProgress>(`/api/lessons/${slug}/complete`),
  saveScratch: (slug: string, files: Record<string, string>, notes?: string) =>
    api.put<LessonProgress>(`/api/lessons/${slug}/scratch`, { files, notes }),
  recordTime: (slug: string, seconds: number) =>
    api.post<LessonProgress>(`/api/lessons/${slug}/time`, { seconds }),
};

export const exercises = {
  detail: (slug: string) => api.get<ExerciseDetail>(`/api/exercises/${slug}`),
  /**
   * Grade an attempt.
   *
   * Graders that need the code to have *run* (stdout-match, pytest) get an
   * `execution_plan` on the exercise; we execute it here in the browser and
   * send the output along for the server to grade. Graders that read the source
   * alone (static assertions, multiple choice) have no plan and need no run.
   */
  submit: async (
    slug: string,
    body: {
      files: Record<string, string>;
      selected_index?: number | null;
      time_spent_seconds?: number;
    },
    plan?: ExecutionPlan | null,
  ): Promise<SubmissionResponse> => {
    let executed: ExecuteResponse | null = null;
    if (plan) {
      executed = await pyodide.run({
        // Hidden tests must not be editable by the learner, so they are merged
        // last and win over any same-named file in the submission.
        files: { ...body.files, ...plan.extra_files },
        mode: plan.mode,
        entrypoint: plan.entrypoint,
        stdin: plan.stdin,
      });
    }
    return api.post<SubmissionResponse>(`/api/exercises/${slug}/submit`, {
      ...body,
      execution: executed ? reportable(executed) : undefined,
    });
  },
  hint: (slug: string, level: number) => api.post<Hint>(`/api/exercises/${slug}/hints/${level}`),
  solution: (slug: string) =>
    api.post<{ files: Record<string, string>; explanation: string }>(
      `/api/exercises/${slug}/solution`,
    ),
  remediation: (slug: string) =>
    api.get<Remediation | null>(`/api/exercises/${slug}/remediation`),
  challenges: (query?: { kind?: string; level?: string }) =>
    api.get<ChallengeSummary[]>('/api/challenges', query),
  catalogue: (query?: { concept?: string; kind?: string; level?: string; limit?: number }) =>
    api.get<ChallengeSummary[]>('/api/exercises', query),
};

/**
 * Client-reported execution, as the API expects it.
 *
 * `error_explanation` is deliberately dropped: the server derives it from the
 * traceback, so sending ours back would be circular.
 */
function reportable(result: ExecuteResponse) {
  return {
    exit_code: result.exit_code,
    stdout: result.stdout,
    stderr: result.stderr,
    timed_out: result.timed_out,
    duration_ms: result.duration_ms,
    stdout_truncated: result.stdout_truncated,
    stderr_truncated: result.stderr_truncated,
  };
}

export const execution = {
  /**
   * Run code in the browser, then tell the server about it.
   *
   * Pyodide produces the result; the round-trip exists only so the run lands in
   * history, analytics and the streak counter. A failed report must not lose
   * the learner their output, so the network error is swallowed.
   */
  run: async (body: {
    files: Record<string, string>;
    entrypoint?: string;
    mode?: 'script' | 'pytest';
    stdin?: string;
    lesson_slug?: string;
    exercise_slug?: string;
  }): Promise<ExecuteResponse> => {
    const result = await pyodide.run({
      files: body.files,
      mode: body.mode,
      entrypoint: body.entrypoint,
      stdin: body.stdin,
    });
    try {
      return await api.post<ExecuteResponse>('/api/execution/run', {
        ...body,
        execution: reportable(result),
      });
    } catch {
      return result;
    }
  },
  health: () => api.get<ExecutionHealth>('/api/execution/health'),
  snippets: () =>
    api.get<
      Array<{
        id: string;
        name: string;
        description: string;
        entrypoint: string;
        files: Record<string, string>;
        updated_at: string;
      }>
    >('/api/execution/snippets'),
  saveSnippet: (name: string, files: Record<string, string>, entrypoint: string) =>
    api.put<{ message: string }>(`/api/execution/snippets/${encodeURIComponent(name)}`, {
      files,
      entrypoint,
    }),
  deleteSnippet: (name: string) =>
    api.delete<{ message: string }>(`/api/execution/snippets/${encodeURIComponent(name)}`),
};

export const progress = {
  dashboard: () => api.get<Dashboard>('/api/dashboard'),
  mastery: () => api.get<MasteryOverview>('/api/mastery'),
  readiness: () =>
    api.get<
      Array<{
        concept_slug: string;
        concept_name: string;
        level: string;
        category: string;
        score: number;
        band: string;
        ready: boolean;
        blocked_by: string[];
      }>
    >('/api/mastery/readiness'),
  recommendations: () => api.get<Recommendation[]>('/api/recommendations'),
  achievements: () => api.get<Achievement[]>('/api/achievements'),
  certifications: () => api.get<CertificationStatus[]>('/api/certifications'),
  claimCertification: (level: string) =>
    api.post<CertificationStatus>(`/api/certifications/${level}/claim`),
};

export const projects = {
  list: () => api.get<ProjectSummary[]>('/api/projects'),
  detail: (slug: string) => api.get<ProjectDetail>(`/api/projects/${slug}`),
  saveWorkspace: (
    slug: string,
    body: {
      files: Record<string, string>;
      entrypoint?: string;
      completed_milestones?: string[];
      notes?: string;
    },
  ) => api.put<ProjectDetail['workspace']>(`/api/projects/${slug}/workspace`, body),
  run: (slug: string) => api.post<ExecuteResponse>(`/api/projects/${slug}/run`),
  submit: (slug: string, files: Record<string, string>) =>
    api.post<ProjectSubmission>(`/api/projects/${slug}/submit`, { files }),
  history: (slug: string) => api.get<ProjectSubmission[]>(`/api/projects/${slug}/submissions`),
};

export const tutor = {
  status: () => api.get<AIStatus>('/api/ai/status'),
  conversations: () => api.get<ConversationDetail[]>('/api/ai/conversations'),
  start: (body: { mode?: string; title?: string; lesson_slug?: string; exercise_slug?: string }) =>
    api.post<ConversationDetail>('/api/ai/conversations', body),
  conversation: (id: string) => api.get<ConversationDetail>(`/api/ai/conversations/${id}`),
  send: (
    id: string,
    body: { message: string; mode?: string; code?: string; error_output?: string },
  ) => api.post<{ id: string; role: string; content: string; meta: Record<string, unknown> }>(
    `/api/ai/conversations/${id}/messages`,
    body,
  ),
};

export const reference = {
  list: (query?: { module?: string; kind?: string; limit?: number }) =>
    api.get<ReferenceSummary[]>('/api/reference', query),
  entry: (key: string) => api.get<ReferenceDetail>(`/api/reference/${key}`),
};

export const search = (q: string, kinds?: string) =>
  api.get<SearchResponse>('/api/search', { q, kinds });

export const codeReview = (files: Record<string, string>) =>
  api.post<ReviewResponse>('/api/code-review', { files });

export const interview = {
  questions: (query?: { track?: string; level?: string; limit?: number }) =>
    api.get<QuizQuestion[]>('/api/interview/questions', query),
  answer: (slug: string, selectedIndex: number) =>
    api.post<QuizAnswer>('/api/interview/answer', { slug, selected_index: selectedIndex }),
};
