/**
 * The API surface, served from the browser.
 *
 * A drop-in replacement for `endpoints.http.ts` used when the app is published
 * with no backend. Reads come from the JSON tree `tools/export_static.py`
 * pre-rendered out of the real API; writes go to localStorage; grading, review
 * and execution run in Pyodide.
 *
 * Every function here has to keep the signature its HTTP twin has — `endpoints.ts`
 * asserts that with `typeof http`, so a mismatch is a compile error rather than a
 * runtime surprise.
 *
 * Some endpoints have no honest static answer. Those degrade explicitly rather
 * than pretending: the AI tutor reports itself unavailable, and certifications
 * cannot be claimed. Each one says so where it happens.
 */

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
  ExerciseDetail,
  ExecutionPlan,
  Hint,
  LessonDetail,
  LessonProgress,
  MasteryItem,
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

import * as pyodide from '@/execution/runner';
import { load, loadOptional } from '@/static/content';
import * as mastery from '@/static/mastery';
import * as store from '@/static/store';

/** The exported exercise document: the API's shape plus the gated extras. */
interface StaticExercise extends ExerciseDetail {
  hints: Hint[];
  solution: { files: Record<string, string>; explanation: string };
  grader_config: Record<string, unknown>;
  misconception_rules: Array<{ pattern: string; misconception: string }>;
}

interface StaticConcept {
  slug: string;
  name: string;
  category: string;
  level: string;
}

interface SearchEntry {
  kind: string;
  slug: string;
  title: string;
  snippet: string;
  url: string;
}

const nowISO = () => new Date().toISOString();

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------

/**
 * The local profile.
 *
 * There is no account and no sign-in: everyone who opens the page is the same
 * anonymous learner, whose record lives in their own browser.
 */
function localUser(): User {
  const progress = store.read();
  return {
    id: 'local',
    email: '',
    display_name: progress.display_name,
    role: 'learner',
    declared_level: 'beginner',
    goal: null,
    xp: progress.xp,
    streak_days: progress.streak_days,
    longest_streak_days: progress.longest_streak_days,
    last_active_on: progress.last_active_on,
    total_coding_seconds: progress.total_coding_seconds,
    preferences: {},
    created_at: progress.created_at,
  };
}

function authResponse(): AuthResponse {
  return {
    user: localUser(),
    tokens: {
      access_token: 'local',
      refresh_token: 'local',
      token_type: 'bearer',
      expires_in_seconds: 0,
    },
  };
}

export const auth = {
  /** No accounts exist, so "registering" just names the local profile. */
  register: async (body: {
    email: string;
    password: string;
    display_name: string;
    declared_level?: string;
    goal?: string;
  }): Promise<AuthResponse> => {
    store.update((progress) => {
      progress.display_name = body.display_name.trim() || 'Learner';
    });
    return authResponse();
  },
  login: async (_body: { email: string; password: string }): Promise<AuthResponse> =>
    authResponse(),
  me: async (): Promise<User> => localUser(),
  updateProfile: async (
    body: Partial<Pick<User, 'display_name' | 'goal'>> & Record<string, unknown>,
  ): Promise<User> => {
    store.update((progress) => {
      if (typeof body.display_name === 'string' && body.display_name.trim()) {
        progress.display_name = body.display_name.trim();
      }
    });
    return localUser();
  },
};

// ---------------------------------------------------------------------------
// Curriculum
// ---------------------------------------------------------------------------

function lessonProgress(slug: string): LessonProgress {
  const progress = store.read();
  const stored = progress.lessons[slug];
  return {
    status: stored?.status ?? 'not_started',
    view_count: stored?.view_count ?? 0,
    exercises_completed: 0,
    exercises_total: 0,
    time_spent_seconds: stored?.time_spent_seconds ?? 0,
    scratch_files: stored?.scratch_files ?? {},
    notes: stored?.notes ?? '',
    completed_at: stored?.completed_at ?? null,
  };
}

function ensureLesson(slug: string): store.StoredLesson {
  const progress = store.read();
  progress.lessons[slug] ??= {
    status: 'not_started',
    view_count: 0,
    time_spent_seconds: 0,
    scratch_files: {},
    notes: '',
    completed_at: null,
  };
  return progress.lessons[slug];
}

export const curriculum = {
  courses: () => load<CourseSummary[]>('courses.json'),
  course: (slug: string) => load<CourseDetail>(`courses/${slug}.json`),
  /** Overlays local progress onto the exported lesson so the UI reflects it. */
  lesson: async (slug: string): Promise<LessonDetail> => {
    const lesson = await load<LessonDetail>(`lessons/${slug}.json`);
    const local = store.read();
    return {
      ...lesson,
      progress: lessonProgress(slug),
      exercises: lesson.exercises.map((exercise) => ({
        ...exercise,
        best_score: store.bestScore(local, exercise.slug),
        status: store.hasPassed(local, exercise.slug)
          ? 'passed'
          : store.attemptsFor(local, exercise.slug).length
            ? 'attempted'
            : 'not_attempted',
      })),
    };
  },
  viewLesson: async (slug: string): Promise<LessonProgress> => {
    store.update((progress) => {
      const lesson = ensureLesson(slug);
      lesson.view_count += 1;
      if (lesson.status === 'not_started') lesson.status = 'in_progress';
      store.touchStreak(progress);
    });
    return lessonProgress(slug);
  },
  completeLesson: async (slug: string): Promise<LessonProgress> => {
    store.update((progress) => {
      const lesson = ensureLesson(slug);
      lesson.status = 'completed';
      lesson.completed_at ??= nowISO();
      store.touchStreak(progress);
    });
    return lessonProgress(slug);
  },
  saveScratch: async (
    slug: string,
    files: Record<string, string>,
    notes?: string,
  ): Promise<LessonProgress> => {
    store.update(() => {
      const lesson = ensureLesson(slug);
      lesson.scratch_files = files;
      if (notes !== undefined) lesson.notes = notes;
    });
    return lessonProgress(slug);
  },
  recordTime: async (slug: string, seconds: number): Promise<LessonProgress> => {
    store.update((progress) => {
      const lesson = ensureLesson(slug);
      lesson.time_spent_seconds += Math.max(0, seconds);
      progress.total_coding_seconds += Math.max(0, seconds);
    });
    return lessonProgress(slug);
  },
};

// ---------------------------------------------------------------------------
// Exercises
// ---------------------------------------------------------------------------

async function exerciseDocument(slug: string): Promise<StaticExercise> {
  return load<StaticExercise>(`exercises/${slug}.json`);
}

/** Overlay the learner's own attempt history onto the exported document. */
function withLocalState(document: StaticExercise): ExerciseDetail {
  const progress = store.read();
  const attempts = store.attemptsFor(progress, document.slug);
  const passed = store.hasPassed(progress, document.slug);
  const hintsRevealed = progress.hints[document.slug] ?? 0;
  const solutionViewed = progress.solutionsViewed.includes(document.slug);
  return {
    ...document,
    hint_count: document.hints.length,
    hints_revealed: hintsRevealed,
    // Mirrors the server rule: three attempts, every hint taken, or a pass.
    solution_unlocked:
      solutionViewed ||
      passed ||
      attempts.length >= 3 ||
      (document.hints.length > 0 && hintsRevealed >= document.hints.length),
    attempts: attempts.length,
    best_score: store.bestScore(progress, document.slug),
    status: passed ? 'passed' : attempts.length ? 'attempted' : 'not_attempted',
  };
}

export const exercises = {
  detail: async (slug: string): Promise<ExerciseDetail> =>
    withLocalState(await exerciseDocument(slug)),

  /**
   * Run the exercise if it needs running, grade it, and record the outcome.
   *
   * This is the static build's version of `SubmissionService.submit`: execute,
   * grade, move mastery, award XP, touch the streak — in that order, because
   * mastery depends on the grade and XP depends on both.
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
    const document = await exerciseDocument(slug);
    const effectivePlan = plan ?? document.execution_plan;
    const merged = { ...document.starter_files, ...body.files };

    let executed: ExecuteResponse | null = null;
    if (effectivePlan) {
      executed = await pyodide.run({
        // Hidden tests win over any same-named file in the submission.
        files: { ...merged, ...effectivePlan.extra_files },
        mode: effectivePlan.mode,
        entrypoint: effectivePlan.entrypoint,
        stdin: effectivePlan.stdin,
      });
    }

    const verdict = await pyodide.grade({
      exercise: {
        slug: document.slug,
        grader: document.grader,
        grader_config: document.grader_config,
        misconception_rules: document.misconception_rules,
      },
      files: merged,
      execution: executed
        ? {
            exit_code: executed.exit_code,
            stdout: executed.stdout,
            stderr: executed.stderr,
            timed_out: executed.timed_out,
            duration_ms: executed.duration_ms,
            error: executed.error,
          }
        : null,
      selected_index: body.selected_index ?? null,
    });

    const before = store.read();
    const attemptNumber = store.attemptsFor(before, slug).length + 1;
    const alreadyPassed = store.hasPassed(before, slug);
    const hintsUsed = before.hints[slug] ?? 0;
    const solutionViewed = before.solutionsViewed.includes(slug);
    const status = verdict.status as SubmissionResponse['status'];

    // Snapshot the concepts this exercise touches so the UI can show movement.
    const conceptNames = await conceptIndex();
    const previous = new Map(
      document.concept_slugs.map((conceptSlug) => [
        conceptSlug,
        mastery.view(conceptSlug, before.concepts[conceptSlug]).score,
      ]),
    );

    let xpAwarded = 0;

    store.update((progress) => {
      progress.submissions.push({
        exercise_slug: slug,
        attempt_number: attemptNumber,
        status,
        score: verdict.score,
        created_at: nowISO(),
        time_spent_seconds: body.time_spent_seconds ?? 0,
        hints_used: hintsUsed,
        solution_viewed: solutionViewed,
        misconceptions: verdict.misconceptions,
      });

      for (const conceptSlug of document.concept_slugs) {
        progress.concepts[conceptSlug] = mastery.record(progress.concepts[conceptSlug], {
          rawScore: verdict.score,
          difficulty: document.difficulty,
          hintsUsed,
          solutionViewed,
          timeSpentSeconds: body.time_spent_seconds ?? 0,
          expectedSeconds: document.estimated_minutes * 60,
        });
      }

      // XP once per exercise, so resubmitting a solved exercise earns nothing.
      if (status === 'passed' && !alreadyPassed) {
        xpAwarded = mastery.xpFor(document.xp_reward, {
          firstAttempt: attemptNumber === 1,
          hintsUsed,
          solutionViewed,
        });
        progress.xp += xpAwarded;
      }

      progress.total_coding_seconds += Math.max(0, body.time_spent_seconds ?? 0);
      store.touchStreak(progress);
    });

    const after = store.read();
    const deltas = document.concept_slugs.map((conceptSlug) => {
      const view = mastery.view(conceptSlug, after.concepts[conceptSlug]);
      const was = previous.get(conceptSlug) ?? 0;
      return {
        concept_slug: conceptSlug,
        concept_name: conceptNames.get(conceptSlug)?.name ?? conceptSlug,
        previous: Math.round(was * 10_000) / 10_000,
        current: view.score,
        delta: Math.round((view.score - was) * 10_000) / 10_000,
        band: view.band,
      };
    });

    return {
      id: `local-${slug}-${attemptNumber}`,
      exercise_slug: slug,
      attempt_number: attemptNumber,
      status,
      score: verdict.score,
      checks: verdict.checks as SubmissionResponse['checks'],
      feedback: verdict.feedback,
      stdout: executed?.stdout ?? '',
      stderr: executed?.stderr ?? '',
      duration_ms: executed?.duration_ms ?? 0,
      hints_used: hintsUsed,
      xp_awarded: xpAwarded,
      mastery_deltas: deltas,
      newly_earned_achievements: [],
      created_at: nowISO(),
    };
  },

  /**
   * Reveal one hint rung.
   *
   * The ladder is still enforced in order, because taking hints one at a time is
   * the point of it — but with the text already in the browser this is guidance
   * rather than a control.
   */
  hint: async (slug: string, level: number): Promise<Hint> => {
    const document = await exerciseDocument(slug);
    const hint = document.hints.find((item) => item.level === level);
    if (!hint) throw new Error(`This exercise has no hint at level ${level}.`);

    store.update((progress) => {
      progress.hints[slug] = Math.max(progress.hints[slug] ?? 0, level);
    });
    return hint;
  },

  solution: async (slug: string): Promise<{ files: Record<string, string>; explanation: string }> => {
    const document = await exerciseDocument(slug);
    store.update((progress) => {
      if (!progress.solutionsViewed.includes(slug)) progress.solutionsViewed.push(slug);
    });
    return document.solution;
  },

  /**
   * Remediation is produced by the adaptive service, which has no static
   * equivalent — it needs cross-learner misconception data. Returning null is
   * the documented "nothing to suggest" answer, so the UI already handles it.
   */
  remediation: async (_slug: string): Promise<Remediation | null> => null,

  challenges: async (query?: { kind?: string; level?: string }): Promise<ChallengeSummary[]> => {
    const all = await load<ChallengeSummary[]>('challenges.json');
    return withSummaryState(
      all.filter(
        (item) =>
          (!query?.kind || item.challenge_kind === query.kind) &&
          (!query?.level || item.level === query.level),
      ),
    );
  },

  catalogue: async (query?: {
    concept?: string;
    kind?: string;
    level?: string;
    limit?: number;
  }): Promise<ChallengeSummary[]> => {
    const all = await load<ChallengeSummary[]>('exercises.json');
    const filtered = all.filter(
      (item) =>
        (!query?.kind || item.kind === query.kind) && (!query?.level || item.level === query.level),
    );
    return withSummaryState(filtered.slice(0, query?.limit ?? filtered.length));
  },
};

/** Overlay attempt state onto a list of exercise summaries. */
function withSummaryState<T extends { slug: string; best_score: number; status: string }>(
  items: T[],
): T[] {
  const progress = store.read();
  return items.map((item) => ({
    ...item,
    best_score: store.bestScore(progress, item.slug),
    status: store.hasPassed(progress, item.slug)
      ? 'passed'
      : store.attemptsFor(progress, item.slug).length
        ? 'attempted'
        : 'not_attempted',
  }));
}

// ---------------------------------------------------------------------------
// Execution
// ---------------------------------------------------------------------------

export const execution = {
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
    store.update((progress) => {
      store.touchStreak(progress);
    });
    return result;
  },

  health: async (): Promise<ExecutionHealth> => ({
    backend: 'pyodide',
    healthy: true,
    // The browser's WASM sandbox, on the learner's own machine.
    isolated: true,
    timeout_seconds: 10,
    memory_mb: 0,
    max_files: 25,
  }),

  warmUp: async (): Promise<void> => {
    pyodide.warmUp();
  },

  snippets: async () => {
    const progress = store.read();
    return Object.entries(progress.snippets)
      .map(([name, snippet]) => ({
        id: name,
        name,
        description: '',
        entrypoint: snippet.entrypoint,
        files: snippet.files,
        updated_at: snippet.updated_at,
      }))
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  },

  saveSnippet: async (name: string, files: Record<string, string>, entrypoint: string) => {
    store.update((progress) => {
      progress.snippets[name] = { files, entrypoint, updated_at: nowISO() };
    });
    return { message: `Saved '${name}'.` };
  },

  deleteSnippet: async (name: string) => {
    store.update((progress) => {
      delete progress.snippets[name];
    });
    return { message: `Deleted '${name}'.` };
  },
};

// ---------------------------------------------------------------------------
// Progress
// ---------------------------------------------------------------------------

/** Concept metadata, so mastery can be shown with names rather than slugs. */
async function conceptIndex(): Promise<Map<string, StaticConcept>> {
  const concepts = await load<StaticConcept[]>('concepts.json');
  return new Map(concepts.map((concept) => [concept.slug, concept]));
}

async function masteryItems(): Promise<MasteryItem[]> {
  const progress = store.read();
  const index = await conceptIndex();
  return mastery.overview(progress).map((item) => {
    const concept = index.get(item.concept_slug);
    return {
      concept_slug: item.concept_slug,
      concept_name: concept?.name ?? item.concept_slug,
      category: concept?.category ?? 'general',
      level: (concept?.level ?? 'beginner') as MasteryItem['level'],
      score: item.score,
      percent: Math.round(item.score * 100),
      confidence: item.confidence,
      band: item.band,
      attempts: item.attempts,
      accuracy: item.score,
      hints_used: 0,
      is_mastered: item.is_mastered,
      last_practiced_at: item.last_practiced_at,
      top_misconceptions: [],
    };
  });
}

/** XP curve, mirroring the server's level bands. */
function levelFor(xp: number): Dashboard['level'] {
  const titles = [
    'Absolute Beginner',
    'Novice',
    'Apprentice',
    'Practitioner',
    'Developer',
    'Senior Developer',
    'Engineer',
    'Principal Engineer',
  ];
  // Each level costs 250 XP more than the last, so progress slows as it should.
  let level = 1;
  let spent = 0;
  let cost = 500;
  while (xp - spent >= cost && level < titles.length) {
    spent += cost;
    cost += 250;
    level += 1;
  }
  const into = xp - spent;
  return {
    level,
    title: titles[level - 1] ?? titles[titles.length - 1]!,
    xp,
    xp_into_level: into,
    xp_for_next_level: cost,
    progress: cost ? Math.min(1, into / cost) : 1,
  };
}

export const progress = {
  dashboard: async (): Promise<Dashboard> => {
    const local = store.read();
    const items = await masteryItems();
    const [courses, projectList] = await Promise.all([
      load<CourseSummary[]>('courses.json'),
      load<ProjectSummary[]>('projects.json'),
    ]);

    const lessonsTotal = courses.reduce((total, course) => total + (course.lesson_count ?? 0), 0);
    const lessonsCompleted = Object.values(local.lessons).filter(
      (lesson) => lesson.status === 'completed',
    ).length;
    const passedAttempts = local.submissions.filter((item) => item.status === 'passed').length;
    const attempted = new Set(local.submissions.map((item) => item.exercise_slug));
    const passedExercises = new Set(
      local.submissions.filter((item) => item.status === 'passed').map((item) => item.exercise_slug),
    );
    const overall = items.length
      ? items.reduce((sum, item) => sum + item.score, 0) / items.length
      : 0;

    const catalogue = await load<ChallengeSummary[]>('exercises.json');
    const titles = new Map(catalogue.map((item) => [item.slug, item.title]));

    return {
      user: { display_name: local.display_name, declared_level: 'beginner', goal: null },
      overall_mastery: Math.round(overall * 10_000) / 10_000,
      level: levelFor(local.xp),
      streak: {
        current_days: local.streak_days,
        longest_days: local.longest_streak_days,
        last_active_on: local.last_active_on,
      },
      counters: {
        total_attempts: local.submissions.length,
        passed_attempts: passedAttempts,
        attempt_accuracy: local.submissions.length
          ? Math.round((passedAttempts / local.submissions.length) * 10_000) / 10_000
          : 0,
        exercises_attempted: attempted.size,
        exercises_passed: passedExercises.size,
        lessons_completed: lessonsCompleted,
        lessons_total: lessonsTotal,
        projects_completed: Object.values(local.projects).filter((p) => p.milestones.length).length,
        projects_total: projectList.length,
        coding_hours: Math.round((local.total_coding_seconds / 3600) * 10) / 10,
        concepts_mastered: items.filter((item) => item.is_mastered).length,
      },
      weak_areas: items
        .filter((item) => item.attempts > 0 && item.score < 0.6)
        .slice(-5)
        .reverse()
        .map((item) => ({
          concept_slug: item.concept_slug,
          concept_name: item.concept_name,
          score: item.score,
          band: item.band,
          misconceptions: [],
        })),
      strong_areas: items
        .filter((item) => item.score >= 0.7)
        .slice(0, 5)
        .map((item) => ({
          concept_slug: item.concept_slug,
          concept_name: item.concept_name,
          score: item.score,
        })),
      recommendations: await progress.recommendations(),
      recent_activity: [...local.submissions]
        .reverse()
        .slice(0, 10)
        .map((item) => ({
          exercise_slug: item.exercise_slug,
          exercise_title: titles.get(item.exercise_slug) ?? item.exercise_slug,
          status: item.status,
          score: item.score,
          at: item.created_at,
        })),
      achievements: [],
      certifications: [],
      activity_series: activitySeries(local),
      repeated_mistakes: repeatedMistakes(local),
    };
  },

  mastery: async (): Promise<MasteryOverview> => {
    const items = await masteryItems();
    const overall = items.length
      ? items.reduce((sum, item) => sum + item.score, 0) / items.length
      : 0;
    return {
      overall: Math.round(overall * 10_000) / 10_000,
      concepts: items,
      weak_areas: items.filter((item) => item.attempts > 0 && item.score < 0.6).reverse(),
      strong_areas: items.filter((item) => item.score >= 0.7),
      mastered_count: items.filter((item) => item.is_mastered).length,
    };
  },

  /**
   * Prerequisite readiness needs the concept graph's edges, which the concept
   * export does not carry, so nothing is reported as blocked.
   */
  readiness: async () => {
    const items = await masteryItems();
    return items.map((item) => ({
      concept_slug: item.concept_slug,
      concept_name: item.concept_name,
      level: item.level as string,
      category: item.category,
      score: item.score,
      band: item.band,
      ready: true,
      blocked_by: [] as string[],
    }));
  },

  /**
   * Recommendations, from what this browser knows.
   *
   * The server's adaptive service also weighs cross-learner misconception data;
   * this is the subset computable from one learner's own record — revisit what
   * is weak, otherwise carry on with the next unattempted exercise.
   */
  recommendations: async (): Promise<Recommendation[]> => {
    const local = store.read();
    const items = await masteryItems();
    const out: Recommendation[] = [];

    for (const item of items.filter((entry) => entry.attempts > 0 && entry.score < 0.5).slice(0, 3)) {
      out.push({
        kind: 'review',
        title: `Revisit ${item.concept_name}`,
        reason: `Your mastery here is ${item.percent}%. A little practice will move it.`,
        lesson_slug: null,
        exercise_slug: null,
        concept_slug: item.concept_slug,
        priority: 1,
      });
    }

    const catalogue = await load<ChallengeSummary[]>('exercises.json');
    const next = catalogue.find((item) => !store.attemptsFor(local, item.slug).length);
    if (next) {
      out.push({
        kind: 'continue',
        title: next.title,
        reason: 'The next exercise you have not tried yet.',
        lesson_slug: null,
        exercise_slug: next.slug,
        concept_slug: null,
        priority: 2,
      });
    }
    return out;
  },

  achievements: async (): Promise<Achievement[]> => [],

  /**
   * Certification requires assessed project submissions against a rubric, which
   * is a server judgement. Reporting none is honest; claiming would be theatre.
   */
  certifications: async (): Promise<CertificationStatus[]> => [],

  claimCertification: async (_level: string): Promise<CertificationStatus> => {
    throw new Error('Certification is not available in the browser-only build.');
  },
};

/**
 * Submissions per day for the last 60 days, for the activity chart.
 *
 * Only submissions are counted. The server also tracks runs, hints and lesson
 * views as separate event streams; this build does not keep an event log, so
 * those read zero rather than being invented.
 */
function activitySeries(local: store.Progress): Dashboard['activity_series'] {
  const counts = new Map<string, number>();
  for (const submission of local.submissions) {
    const day = submission.created_at.slice(0, 10);
    counts.set(day, (counts.get(day) ?? 0) + 1);
  }
  const series: Dashboard['activity_series'] = [];
  for (let offset = 59; offset >= 0; offset -= 1) {
    const date = new Date();
    date.setDate(date.getDate() - offset);
    const key = date.toISOString().slice(0, 10);
    series.push({
      date: key,
      runs: 0,
      submissions: counts.get(key) ?? 0,
      lessons: 0,
      hints: 0,
    });
  }
  return series;
}

/** Misconceptions seen more than once, commonest first. */
function repeatedMistakes(local: store.Progress): Dashboard['repeated_mistakes'] {
  const counts = new Map<string, number>();
  for (const submission of local.submissions) {
    for (const slug of submission.misconceptions ?? []) {
      counts.set(slug, (counts.get(slug) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .filter(([, count]) => count > 1)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([misconception, count]) => ({
      misconception,
      count,
      // The server has an authored label table; a readable slug is the honest
      // fallback rather than shipping a second copy of that mapping.
      label: misconception.replace(/-/g, ' ').replace(/^./, (c) => c.toUpperCase()),
    }));
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export const projects = {
  list: () => load<ProjectSummary[]>('projects.json'),

  detail: async (slug: string): Promise<ProjectDetail> => {
    const project = await load<ProjectDetail>(`projects/${slug}.json`);
    const saved = store.read().projects[slug];
    if (!saved) return project;
    return {
      ...project,
      workspace: {
        files: saved.files,
        entrypoint: saved.entrypoint,
        completed_milestones: saved.milestones,
        notes: saved.notes,
        updated_at: saved.updated_at,
      },
    };
  },

  saveWorkspace: async (
    slug: string,
    body: {
      files: Record<string, string>;
      entrypoint?: string;
      completed_milestones?: string[];
      notes?: string;
    },
  ) => {
    store.update((local) => {
      const existing = local.projects[slug];
      local.projects[slug] = {
        files: body.files,
        entrypoint: body.entrypoint ?? existing?.entrypoint ?? 'main.py',
        milestones: body.completed_milestones ?? existing?.milestones ?? [],
        notes: body.notes ?? existing?.notes ?? '',
        updated_at: nowISO(),
      };
    });
    const project = await projects.detail(slug);
    return project.workspace;
  },

  run: async (slug: string): Promise<ExecuteResponse> => {
    const project = await projects.detail(slug);
    // A project that has never been opened has no saved workspace, so fall back
    // to the brief's starter files.
    const files = project.workspace?.files ?? project.starter_files ?? {};
    return pyodide.run({
      files,
      entrypoint: project.workspace?.entrypoint ?? 'main.py',
    });
  },

  /**
   * Projects are assessed against an engineering rubric by the server. What the
   * browser *can* do honestly is run the code and review it, so a submission
   * here reports the code-review verdict rather than inventing a rubric score.
   */
  submit: async (slug: string, files: Record<string, string>): Promise<ProjectSubmission> => {
    const executed = await pyodide.run({ files, entrypoint: 'main.py' });
    const review = (await pyodide.review(files)) as ReviewResponse;
    return {
      id: `local-${slug}`,
      project_slug: slug,
      attempt_number: 1,
      verdict: review.overall_score >= 0.7 ? 'passed' : 'needs_work',
      overall_score: review.overall_score,
      tests_passed: 0,
      tests_total: 0,
      rubric_scores: Object.entries(review.dimension_scores).map(([key, score]) => ({
        key,
        label: key.replace(/_/g, ' '),
        score,
        comment: '',
      })),
      review_markdown: review.summary,
      stdout: executed.stdout,
      stderr: executed.stderr,
      xp_awarded: 0,
    } as ProjectSubmission;
  },

  history: async (_slug: string): Promise<ProjectSubmission[]> => [],
};

// ---------------------------------------------------------------------------
// AI tutor
// ---------------------------------------------------------------------------

/**
 * The tutor needs a model, and a public static site has nowhere to keep an API
 * key — one in the bundle would be one anybody could spend. So it reports itself
 * unavailable and the UI shows its offline state.
 */
export const tutor = {
  status: async (): Promise<AIStatus> => ({
    backend: 'unavailable',
    model: null,
    live: false,
    daily_limit: 0,
    used_today: 0,
  }),
  conversations: async (): Promise<ConversationDetail[]> => [],
  start: async (_body: {
    mode?: string;
    title?: string;
    lesson_slug?: string;
    exercise_slug?: string;
  }): Promise<ConversationDetail> => {
    throw new Error(
      'The AI tutor needs a server with a model key, so it is not part of this build. ' +
        'The hint ladder on each exercise is available instead.',
    );
  },
  conversation: async (_id: string): Promise<ConversationDetail> => {
    throw new Error('The AI tutor is not part of this build.');
  },
  send: async (
    _id: string,
    _body: { message: string; mode?: string; code?: string; error_output?: string },
  ) => {
    throw new Error('The AI tutor is not part of this build.');
  },
};

// ---------------------------------------------------------------------------
// Reference, search, review, interview
// ---------------------------------------------------------------------------

export const reference = {
  list: async (query?: {
    module?: string;
    kind?: string;
    limit?: number;
  }): Promise<ReferenceSummary[]> => {
    const entries = await load<ReferenceSummary[]>('reference.json');
    const filtered = entries.filter(
      (entry) =>
        (!query?.module || entry.module === query.module) &&
        (!query?.kind || entry.kind === query.kind),
    );
    return filtered.slice(0, query?.limit ?? filtered.length);
  },
  entry: async (key: string): Promise<ReferenceDetail> => {
    const entry = await loadOptional<ReferenceDetail>(`reference/${key}.json`);
    if (!entry) throw new Error(`No reference entry for '${key}'.`);
    return entry;
  },
};

/**
 * Search over the exported index.
 *
 * The server ranks with SQL; this scores on where the match falls — a title hit
 * beats a body hit, and a prefix beats a substring — which is enough to put the
 * obvious answer first on a corpus this size.
 */
export const search = async (q: string, kinds?: string): Promise<SearchResponse> => {
  const index = await load<SearchEntry[]>('search-index.json');
  const needle = q.trim().toLowerCase();
  if (!needle) return { query: q, total: 0, hits: [] };

  const wanted = kinds ? new Set(kinds.split(',').map((kind) => kind.trim())) : null;
  const hits = index
    .filter((entry) => !wanted || wanted.has(entry.kind))
    .map((entry) => {
      const title = entry.title.toLowerCase();
      const snippet = entry.snippet.toLowerCase();
      let score = 0;
      if (title === needle) score = 1;
      else if (title.startsWith(needle)) score = 0.9;
      else if (title.includes(needle)) score = 0.75;
      else if (entry.slug.toLowerCase().includes(needle)) score = 0.6;
      else if (snippet.includes(needle)) score = 0.4;
      return { ...entry, score, meta: {} };
    })
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title))
    .slice(0, 40);

  return { query: q, total: hits.length, hits };
};

/** The full 11-dimension review, running the backend's own engine in Pyodide. */
export const codeReview = async (files: Record<string, string>): Promise<ReviewResponse> =>
  (await pyodide.review(files)) as ReviewResponse;

interface StaticQuizQuestion extends QuizQuestion {
  correct_index: number;
  explanation: string;
}

export const interview = {
  questions: async (query?: {
    track?: string;
    level?: string;
    limit?: number;
  }): Promise<QuizQuestion[]> => {
    const all = await load<StaticQuizQuestion[]>('interview.json');
    const filtered = all.filter(
      (item) =>
        (!query?.track || item.tracks.includes(query.track)) &&
        (!query?.level || item.level === query.level),
    );
    return filtered.slice(0, query?.limit ?? 20);
  },

  answer: async (slug: string, selectedIndex: number): Promise<QuizAnswer> => {
    const all = await load<StaticQuizQuestion[]>('interview.json');
    const question = all.find((item) => item.slug === slug);
    if (!question) throw new Error(`No interview question '${slug}'.`);
    const correct = selectedIndex === question.correct_index;
    store.update((local) => {
      local.quizAnswers[slug] = { selected_index: selectedIndex, correct };
    });
    return { correct, correct_index: question.correct_index, explanation: question.explanation };
  },
};
