/** Response shapes mirroring the backend Pydantic schemas. */

export type SkillLevel = 'beginner' | 'intermediate' | 'advanced' | 'professional' | 'engineering';

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  declared_level: SkillLevel;
  goal: string | null;
  xp: number;
  streak_days: number;
  longest_streak_days: number;
  last_active_on: string | null;
  total_coding_seconds: number;
  preferences: Record<string, unknown>;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
}

export interface Concept {
  slug: string;
  name: string;
  description: string;
  level: SkillLevel;
  category: string;
  difficulty: number;
  prerequisites: string[];
}

export interface LessonSummary {
  slug: string;
  title: string;
  summary: string;
  level: SkillLevel;
  position: number;
  estimated_minutes: number;
  concept_slugs: string[];
  exercise_count: number;
  status: 'not_started' | 'in_progress' | 'completed';
}

export interface ModuleSummary {
  slug: string;
  title: string;
  summary: string;
  level: SkillLevel;
  position: number;
  estimated_minutes: number;
  lessons: LessonSummary[];
}

export interface CourseSummary {
  slug: string;
  title: string;
  subtitle: string | null;
  description: string;
  level: SkillLevel;
  estimated_hours: number;
  outcomes: string[];
  module_count: number;
  lesson_count: number;
}

export interface CourseDetail extends CourseSummary {
  modules: ModuleSummary[];
}

export interface ExampleBlock {
  title: string;
  code: string;
  output: string;
  explanation: string;
}

export interface ExerciseSummary {
  slug: string;
  title: string;
  kind: string;
  level: SkillLevel;
  difficulty: number;
  estimated_minutes: number;
  xp_reward: number;
  position: number;
  is_challenge: boolean;
  challenge_kind: string | null;
  status: 'not_attempted' | 'attempted' | 'passed';
  best_score: number;
}

/** What `/api/challenges` and `/api/exercises` return: a summary plus the prompt. */
export interface ChallengeSummary extends ExerciseSummary {
  prompt: string;
  time_limit_minutes: number | null;
}

export interface LessonProgress {
  status: string;
  view_count: number;
  exercises_completed: number;
  exercises_total: number;
  time_spent_seconds: number;
  scratch_files: Record<string, string>;
  notes: string;
  completed_at: string | null;
}

export interface LessonDetail {
  slug: string;
  title: string;
  summary: string;
  level: SkillLevel;
  position: number;
  estimated_minutes: number;
  body: string;
  sections: Record<string, string>;
  starter_code: string;
  examples: ExampleBlock[];
  visualizations: Record<string, unknown>[];
  reference_keys: string[];
  xp_reward: number;
  module_slug: string;
  module_title: string;
  course_slug: string;
  concepts: Concept[];
  exercises: ExerciseSummary[];
  progress: LessonProgress | null;
  next_lesson_slug: string | null;
  previous_lesson_slug: string | null;
}

/**
 * How to run an exercise, for a client that executes code itself.
 *
 * Present only when the deployment has no server-side sandbox. `extra_files`
 * carries the hidden test suite, which the browser cannot run without.
 */
export interface ExecutionPlan {
  mode: 'script' | 'pytest';
  entrypoint: string;
  stdin: string;
  pytest_args: string[];
  extra_files: Record<string, string>;
  timeout_seconds: number;
}

export interface ExerciseDetail {
  slug: string;
  title: string;
  prompt: string;
  kind: string;
  level: SkillLevel;
  difficulty: number;
  estimated_minutes: number;
  xp_reward: number;
  starter_files: Record<string, string>;
  grader: string;
  concept_slugs: string[];
  lesson_slug: string | null;
  hint_count: number;
  hints_revealed: number;
  solution_unlocked: boolean;
  time_limit_minutes: number | null;
  attempts: number;
  best_score: number;
  status: string;
  options: string[] | null;
  execution_plan: ExecutionPlan | null;
}

export interface Hint {
  level: number;
  text: string;
  penalty: number;
  is_last: boolean;
}

export interface ExecuteResponse {
  ok: boolean;
  exit_code: number;
  stdout: string;
  stderr: string;
  timed_out: boolean;
  duration_ms: number;
  stdout_truncated: boolean;
  stderr_truncated: boolean;
  error: string | null;
  error_explanation: string | null;
}

export interface Check {
  name: string;
  passed: boolean;
  message: string;
  expected: string | null;
  actual: string | null;
  diff: string | null;
}

export interface MasteryDelta {
  concept_slug: string;
  concept_name: string;
  previous: number;
  current: number;
  delta: number;
  band: string;
}

export interface SubmissionResponse {
  id: string;
  exercise_slug: string;
  attempt_number: number;
  status: 'passed' | 'failed' | 'partial' | 'error' | 'timed_out';
  score: number;
  checks: Check[];
  feedback: string;
  stdout: string;
  stderr: string;
  duration_ms: number;
  hints_used: number;
  xp_awarded: number;
  mastery_deltas: MasteryDelta[];
  newly_earned_achievements: string[];
  created_at: string;
}

export interface MasteryItem {
  concept_slug: string;
  concept_name: string;
  category: string;
  level: SkillLevel;
  score: number;
  percent: number;
  confidence: number;
  band: string;
  attempts: number;
  accuracy: number;
  hints_used: number;
  is_mastered: boolean;
  last_practiced_at: string | null;
  top_misconceptions: string[];
}

export interface MasteryOverview {
  overall: number;
  concepts: MasteryItem[];
  weak_areas: MasteryItem[];
  strong_areas: MasteryItem[];
  mastered_count: number;
}

export interface Recommendation {
  kind: 'remediate' | 'review' | 'continue' | 'advance' | 'project';
  title: string;
  reason: string;
  lesson_slug: string | null;
  exercise_slug: string | null;
  concept_slug: string | null;
  priority: number;
}

export interface Remediation {
  stage: string;
  misconception: string | null;
  misconception_label: string | null;
  explanation: string;
  concept_slug: string | null;
  next_exercise_slug: string | null;
  message: string;
}

export interface Dashboard {
  user: { display_name: string; declared_level: string; goal: string | null };
  overall_mastery: number;
  level: {
    level: number;
    title: string;
    xp: number;
    xp_into_level: number;
    xp_for_next_level: number;
    progress: number;
  };
  streak: { current_days: number; longest_days: number; last_active_on: string | null };
  counters: {
    total_attempts: number;
    passed_attempts: number;
    attempt_accuracy: number;
    exercises_attempted: number;
    exercises_passed: number;
    lessons_completed: number;
    lessons_total: number;
    projects_completed: number;
    projects_total: number;
    coding_hours: number;
    concepts_mastered: number;
  };
  weak_areas: Array<{
    concept_slug: string;
    concept_name: string;
    score: number;
    band: string;
    misconceptions: string[];
  }>;
  strong_areas: Array<{ concept_slug: string; concept_name: string; score: number }>;
  recommendations: Recommendation[];
  recent_activity: Array<{
    exercise_slug: string;
    exercise_title: string;
    status: string;
    score: number;
    at: string;
  }>;
  achievements: Array<{
    slug: string;
    name: string;
    description: string;
    icon: string;
    tier: string;
    earned_at: string;
  }>;
  certifications: Array<{
    level: string;
    awarded_at: string;
    code: string;
    overall_mastery: number;
  }>;
  activity_series: Array<{
    date: string;
    runs: number;
    submissions: number;
    lessons: number;
    hints: number;
  }>;
  repeated_mistakes: Array<{ misconception: string; count: number; label: string }>;
}

export interface ProjectSummary {
  slug: string;
  title: string;
  tagline: string;
  level: SkillLevel;
  guidance: string;
  estimated_hours: number;
  xp_reward: number;
  is_capstone: boolean;
  concept_slugs: string[];
  status: string;
  best_score: number;
}

export interface ProjectWorkspace {
  files: Record<string, string>;
  entrypoint: string;
  completed_milestones: string[];
  notes: string;
  updated_at: string;
}

export interface ProjectDetail extends ProjectSummary {
  requirements: string;
  architecture_notes: string;
  suggested_structure: string;
  milestones: Array<{ key: string; title: string; detail: string }>;
  starter_files: Record<string, string>;
  rubric: Array<{ key: string; label: string; weight: number; description: string }>;
  prerequisite_slugs: string[];
  workspace: ProjectWorkspace | null;
}

export interface ProjectSubmission {
  id: string;
  project_slug: string;
  attempt_number: number;
  verdict: string;
  overall_score: number;
  tests_passed: number;
  tests_total: number;
  rubric_scores: Array<{ key: string; label: string; score: number; comment: string }>;
  review_markdown: string;
  stdout: string;
  stderr: string;
  xp_awarded: number;
  created_at: string;
}

export interface Finding {
  dimension: string;
  severity: 'critical' | 'major' | 'minor' | 'info';
  message: string;
  suggestion: string;
  file: string;
  line: number | null;
}

export interface ReviewResponse {
  findings: Finding[];
  dimension_scores: Record<string, number>;
  overall_score: number;
  summary: string;
  strengths: string[];
}

export interface ReferenceSummary {
  key: string;
  title: string;
  kind: string;
  module: string;
  signature: string;
  summary: string;
}

export interface ReferenceDetail extends ReferenceSummary {
  description: string;
  parameters: Array<{
    name: string;
    type?: string;
    required?: boolean;
    default?: string;
    description: string;
  }>;
  returns: string;
  raises: Array<{ type: string; when: string }>;
  examples: Array<{ title: string; code: string; output?: string }>;
  real_world_usage: string;
  common_mistakes: Array<{ mistake: string; fix: string }>;
  performance_notes: string;
  security_notes: string;
  related_keys: string[];
  exercise_slugs: string[];
  lesson_slugs: string[];
}

export interface SearchHit {
  kind: string;
  slug: string;
  title: string;
  snippet: string;
  score: number;
  url: string;
  meta: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  total: number;
  hits: SearchHit[];
}

export interface Conversation {
  id: string;
  title: string;
  mode: string;
  context: Record<string, unknown>;
  hint_level_reached: number;
  updated_at: string;
}

export interface AIMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: AIMessage[];
}

export interface AIStatus {
  backend: string;
  model: string | null;
  live: boolean;
  daily_limit: number;
  used_today: number;
}

export interface CertificationStatus {
  level: string;
  title: string;
  description: string;
  earned: boolean;
  eligible: boolean;
  progress: number;
  unmet_requirements: string[];
  evidence: Record<string, unknown>;
  awarded_at: string | null;
  certificate_code: string | null;
}

export interface Achievement {
  slug: string;
  name: string;
  description: string;
  icon: string;
  tier: string;
  xp_reward: number;
  earned: boolean;
  earned_at: string | null;
}

export interface QuizQuestion {
  slug: string;
  question: string;
  code_snippet: string | null;
  options: string[];
  category: string;
  level: SkillLevel;
  tracks: string[];
}

export interface QuizAnswer {
  correct: boolean;
  correct_index: number;
  explanation: string;
}

export interface ExecutionHealth {
  backend: string;
  healthy: boolean;
  isolated: boolean;
  timeout_seconds: number;
  memory_mb: number;
  max_files: number;
}
