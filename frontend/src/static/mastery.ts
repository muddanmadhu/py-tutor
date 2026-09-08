/**
 * The mastery engine, ported from `backend/app/services/mastery.py`.
 *
 * This is the one piece of server logic that could not be vendored the way
 * grading was: the Python module is bound to SQLAlchemy, and this runs on every
 * render rather than only inside Pyodide. So it is a deliberate port, and the
 * constants and formulae below are copied from that module — if you change one
 * side, change the other. `backend/tests/test_static_mastery.py` grades the same
 * evidence through both and requires the same numbers, which is what stops them
 * drifting silently.
 *
 * The model, briefly: each graded attempt collapses to an evidence value in
 * [0, 1], which is blended into the stored score with a learning rate that
 * shrinks as confidence grows. Retention decay is applied on *read*, so someone
 * returning after a month sees an honest number without anything having to
 * rewrite their record in the background.
 */

import type { Progress, StoredConcept } from './store';

// --- Tunables, mirroring mastery.py ---------------------------------------
const BASE_LEARNING_RATE = 0.45;
const CONFIDENCE_GAIN = 0.22;
/** Days after which an unpractised concept at zero confidence retains ~37%. */
const BASE_RETENTION_TAU_DAYS = 12.0;
/** Multiplier on tau at full confidence (well-learned material fades slowly). */
const MAX_RETENTION_STRETCH = 9.0;
/** Retention never drives a score below this fraction of its stored value. */
const RETENTION_FLOOR = 0.55;
const MASTERY_THRESHOLD = 0.85;
const MASTERY_MIN_ATTEMPTS = 3;
const MASTERY_MIN_CONFIDENCE = 0.5;
const HINT_PENALTY_PER_LEVEL = 0.12;
const SOLUTION_PENALTY = 0.55;

export type MasteryBand =
  | 'not_started'
  | 'novice'
  | 'learning'
  | 'competent'
  | 'proficient'
  | 'mastered';

export interface Evidence {
  /** Grader score in [0, 1]. */
  rawScore: number;
  /** Item difficulty in [0, 1]. */
  difficulty?: number;
  hintsUsed?: number;
  solutionViewed?: boolean;
  timeSpentSeconds?: number;
  expectedSeconds?: number;
}

function clamp(value: number, low = 0, high = 1): number {
  return Math.max(low, Math.min(high, value));
}

/**
 * Mild credit for fluency, mild discount for a long struggle.
 *
 * Capped tightly on both sides: speed is weak evidence next to correctness, and
 * we never want to push learners to rush.
 */
function paceFactor(evidence: Evidence): number {
  const expected = evidence.expectedSeconds ?? 0;
  const spent = evidence.timeSpentSeconds ?? 0;
  if (!expected || !spent || evidence.rawScore <= 0) return 1.0;
  const ratio = spent / expected;
  if (ratio <= 0.6) return 1.05;
  if (ratio >= 3.0) return 0.9;
  return 1.0;
}

/** Collapse one observation into a single [0, 1] evidence figure. */
export function evidenceValue(evidence: Evidence): number {
  const score = clamp(evidence.rawScore);
  const hintDiscount = Math.max(
    0.35,
    1.0 - HINT_PENALTY_PER_LEVEL * Math.max(0, evidence.hintsUsed ?? 0),
  );
  const solutionDiscount = evidence.solutionViewed ? SOLUTION_PENALTY : 1.0;
  return clamp(score * hintDiscount * solutionDiscount * paceFactor(evidence));
}

/**
 * Where this evidence says the score *should* sit.
 *
 * Succeeding on a difficult item is stronger proof of mastery than succeeding
 * on an easy one, and failing a difficult item is weaker proof of ignorance.
 * Both effects are bounded so difficulty can never manufacture mastery alone.
 */
export function targetFor(value: number, difficulty: number): number {
  const d = clamp(difficulty);
  if (value >= 0.5) return clamp(value + 0.15 * d * value);
  return clamp(value + 0.2 * d * (1.0 - value));
}

/** Exponential forgetting curve, floored so scores never collapse to zero. */
export function retentionFactor(lastPracticed: string | null, confidence: number): number {
  if (!lastPracticed) return 1.0;
  const days = Math.max(0, (Date.now() - new Date(lastPracticed).getTime()) / 86_400_000);
  const tau = BASE_RETENTION_TAU_DAYS * (1.0 + MAX_RETENTION_STRETCH * clamp(confidence));
  return Math.max(RETENTION_FLOOR, Math.exp(-days / tau));
}

/** Map a score onto a band. */
export function bandFor(score: number, attempts = 1): MasteryBand {
  if (attempts === 0) return 'not_started';
  if (score >= MASTERY_THRESHOLD) return 'mastered';
  if (score >= 0.7) return 'proficient';
  if (score >= 0.5) return 'competent';
  if (score >= 0.25) return 'learning';
  return 'novice';
}

/**
 * Confidence implied by a number of independent observations.
 *
 * The Python engine stores confidence and grows it per attempt
 * (`c' = c + (1 - c) × gain`); that closed form is the same sequence, which
 * keeps the stored record smaller and means a replayed history yields the same
 * confidence as an incremental one.
 */
export function confidenceFor(attempts: number): number {
  return 1 - Math.pow(1 - CONFIDENCE_GAIN, Math.max(0, attempts));
}

/** Fold one observation into a concept's stored score. */
export function record(
  concept: StoredConcept | undefined,
  evidence: Evidence,
): StoredConcept {
  const current = concept ?? { score: 0, attempts: 0, last_seen: new Date().toISOString() };
  const value = evidenceValue(evidence);
  const target = targetFor(value, evidence.difficulty ?? 0.5);
  const confidence = confidenceFor(current.attempts);
  // The learning rate shrinks as confidence grows, so early evidence moves the
  // needle quickly and later evidence refines rather than whipsaws.
  const alpha = BASE_LEARNING_RATE * (1 - 0.6 * confidence);
  return {
    score: clamp(current.score + alpha * (target - current.score)),
    attempts: current.attempts + 1,
    last_seen: new Date().toISOString(),
  };
}

export interface MasteryView {
  concept_slug: string;
  score: number;
  confidence: number;
  band: MasteryBand;
  attempts: number;
  is_mastered: boolean;
  last_practiced_at: string | null;
}

/** A concept's mastery as the UI should show it, with decay applied. */
export function view(slug: string, concept: StoredConcept | undefined): MasteryView {
  if (!concept || concept.attempts === 0) {
    return {
      concept_slug: slug,
      score: 0,
      confidence: 0,
      band: 'not_started',
      attempts: 0,
      is_mastered: false,
      last_practiced_at: null,
    };
  }
  const confidence = confidenceFor(concept.attempts);
  const decayed = clamp(concept.score * retentionFactor(concept.last_seen, confidence));
  return {
    concept_slug: slug,
    score: Math.round(decayed * 10_000) / 10_000,
    confidence: Math.round(confidence * 10_000) / 10_000,
    band: bandFor(decayed, concept.attempts),
    attempts: concept.attempts,
    is_mastered:
      decayed >= MASTERY_THRESHOLD &&
      concept.attempts >= MASTERY_MIN_ATTEMPTS &&
      confidence >= MASTERY_MIN_CONFIDENCE,
    last_practiced_at: concept.last_seen,
  };
}

/**
 * XP for a passing submission, discounted by the help that was used.
 *
 * Mirrors `SubmissionService._award_xp`: granted once per exercise, so a
 * learner cannot farm it by resubmitting a solved exercise.
 */
export function xpFor(
  reward: number,
  options: {
    firstAttempt: boolean;
    hintsUsed: number;
    solutionViewed: boolean;
  },
): number {
  let xp = reward;
  if (options.solutionViewed) xp *= 0.3;
  else if (options.hintsUsed) xp *= Math.max(0.4, 1.0 - 0.15 * options.hintsUsed);
  if (options.firstAttempt && !options.hintsUsed && !options.solutionViewed) xp *= 1.25;
  return Math.round(xp);
}

/** Every concept the learner has touched, decayed, best first. */
export function overview(progress: Progress): MasteryView[] {
  return Object.entries(progress.concepts)
    .map(([slug, concept]) => view(slug, concept))
    .sort((a, b) => b.score - a.score);
}
