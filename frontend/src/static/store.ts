/**
 * Local learning record.
 *
 * With no server there is nobody to keep a learner's progress but their own
 * browser, so everything the platform would have stored in Postgres lives in
 * one localStorage document: submissions, lesson state, XP, streak, mastery.
 *
 * Consequences worth being honest about, all of them stated in the UI: progress
 * does not follow anyone to another browser or device, clearing site data wipes
 * it, and nothing here is authoritative — a learner can edit it. That is
 * acceptable because the only person affected is its owner.
 *
 * The whole document is read and rewritten on each change. At the scale of one
 * curriculum (tens of lessons, hundreds of submissions) that is a fraction of a
 * millisecond, and it makes every write atomic.
 */

import type { SubmissionResponse } from '@/api/types';

/** Mirrors the API's submission statuses. */
type SubmissionStatus = SubmissionResponse['status'];

const KEY = 'pyforge.progress';
/** Bumped when the shape changes incompatibly; older documents are discarded. */
const VERSION = 1;

export interface StoredSubmission {
  exercise_slug: string;
  attempt_number: number;
  status: SubmissionStatus;
  score: number;
  created_at: string;
  time_spent_seconds: number;
  hints_used: number;
  solution_viewed: boolean;
  /** Misconception slugs the grader inferred, for the repeated-mistakes view. */
  misconceptions: string[];
}

export interface StoredLesson {
  status: 'not_started' | 'in_progress' | 'completed';
  view_count: number;
  time_spent_seconds: number;
  scratch_files: Record<string, string>;
  notes: string;
  completed_at: string | null;
}

export interface StoredConcept {
  /** Exponential moving average of evidence, in [0, 1]. */
  score: number;
  attempts: number;
  last_seen: string;
}

export interface Progress {
  version: number;
  created_at: string;
  display_name: string;
  xp: number;
  streak_days: number;
  longest_streak_days: number;
  last_active_on: string | null;
  total_coding_seconds: number;
  submissions: StoredSubmission[];
  lessons: Record<string, StoredLesson>;
  concepts: Record<string, StoredConcept>;
  /** Highest hint rung revealed per exercise, so the ladder survives a reload. */
  hints: Record<string, number>;
  solutionsViewed: string[];
  achievements: string[];
  snippets: Record<string, { files: Record<string, string>; entrypoint: string; updated_at: string }>;
  projects: Record<
    string,
    {
      files: Record<string, string>;
      entrypoint: string;
      milestones: string[];
      notes: string;
      updated_at: string;
    }
  >;
  quizAnswers: Record<string, { selected_index: number; correct: boolean }>;
}

function today(): string {
  // Local date, not UTC: a streak should break when *the learner's* day does.
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

function empty(): Progress {
  return {
    version: VERSION,
    created_at: new Date().toISOString(),
    display_name: 'Learner',
    xp: 0,
    streak_days: 0,
    longest_streak_days: 0,
    last_active_on: null,
    total_coding_seconds: 0,
    submissions: [],
    lessons: {},
    concepts: {},
    hints: {},
    solutionsViewed: [],
    achievements: [],
    snippets: {},
    projects: {},
    quizAnswers: {},
  };
}

let cache: Progress | null = null;

/** The learner's record, created on first use. */
export function read(): Progress {
  if (cache) return cache;
  const raw = localStorage.getItem(KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as Progress;
      if (parsed.version === VERSION) {
        // Merge over a fresh document so a field added in a later release is
        // present even on a record written before it existed.
        cache = { ...empty(), ...parsed };
        return cache;
      }
    } catch {
      // Unparseable means unusable; starting fresh beats failing every read.
    }
  }
  cache = empty();
  return cache;
}

/** Apply a change and persist. */
export function update(mutate: (progress: Progress) => void): Progress {
  const progress = read();
  mutate(progress);
  cache = progress;
  try {
    localStorage.setItem(KEY, JSON.stringify(progress));
  } catch {
    // Private browsing, or a full quota. The in-memory copy still works for
    // this session, which is strictly better than throwing mid-submission.
  }
  return progress;
}

/** Discard everything and start over. */
export function reset(): void {
  cache = null;
  localStorage.removeItem(KEY);
}

/** Export the record so a learner can move it between browsers themselves. */
export function toJSON(): string {
  return JSON.stringify(read(), null, 2);
}

/**
 * Replace the record from a previously exported document.
 *
 * Returns false rather than throwing on anything unrecognisable, so the UI can
 * say "that is not a PyForge export" instead of breaking.
 */
export function fromJSON(text: string): boolean {
  try {
    const parsed = JSON.parse(text) as Progress;
    if (typeof parsed !== 'object' || parsed === null || parsed.version !== VERSION) return false;
    cache = { ...empty(), ...parsed };
    localStorage.setItem(KEY, JSON.stringify(cache));
    return true;
  } catch {
    return false;
  }
}

/**
 * Record that the learner did something today, and move the streak.
 *
 * Called on every run and submission, so it has to be idempotent within a day.
 */
export function touchStreak(progress: Progress): void {
  const day = today();
  if (progress.last_active_on === day) return;

  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const month = String(yesterday.getMonth() + 1).padStart(2, '0');
  const date = String(yesterday.getDate()).padStart(2, '0');
  const previous = `${yesterday.getFullYear()}-${month}-${date}`;

  progress.streak_days = progress.last_active_on === previous ? progress.streak_days + 1 : 1;
  progress.longest_streak_days = Math.max(progress.longest_streak_days, progress.streak_days);
  progress.last_active_on = day;
}

/** Attempts recorded against one exercise. */
export function attemptsFor(progress: Progress, slug: string): StoredSubmission[] {
  return progress.submissions.filter((item) => item.exercise_slug === slug);
}

/** The best score achieved on one exercise. */
export function bestScore(progress: Progress, slug: string): number {
  return attemptsFor(progress, slug).reduce((best, item) => Math.max(best, item.score), 0);
}

/** Whether an exercise has ever been passed. */
export function hasPassed(progress: Progress, slug: string): boolean {
  return attemptsFor(progress, slug).some((item) => item.status === 'passed');
}
