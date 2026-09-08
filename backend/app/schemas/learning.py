"""Curriculum, exercise, execution and submission schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from app.models.enums import AIMode, ExecutionMode
from app.schemas.common import APIModel

# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------


class ConceptResponse(APIModel):
    """A masterable concept."""

    slug: str
    name: str
    description: str
    level: str
    category: str
    difficulty: float
    prerequisites: list[str] = Field(default_factory=list)


class LessonSummary(APIModel):
    """A lesson in a listing."""

    slug: str
    title: str
    summary: str
    level: str
    position: int
    estimated_minutes: int
    concept_slugs: list[str] = Field(default_factory=list)
    exercise_count: int = 0
    status: str = "not_started"


class ExampleBlock(APIModel):
    """A worked example inside a lesson."""

    title: str
    code: str
    output: str = ""
    explanation: str = ""


class LessonDetail(APIModel):
    """A lesson with everything needed to render its page."""

    slug: str
    title: str
    summary: str
    level: str
    position: int
    estimated_minutes: int
    body: str
    sections: dict[str, Any]
    starter_code: str
    examples: list[ExampleBlock]
    visualizations: list[dict[str, Any]]
    reference_keys: list[str]
    xp_reward: int
    module_slug: str
    module_title: str
    course_slug: str
    concepts: list[ConceptResponse]
    exercises: list[ExerciseSummary]
    progress: LessonProgressResponse | None = None
    next_lesson_slug: str | None = None
    previous_lesson_slug: str | None = None


class ModuleSummary(APIModel):
    """A module in a course listing."""

    slug: str
    title: str
    summary: str
    level: str
    position: int
    estimated_minutes: int
    lessons: list[LessonSummary]


class CourseSummary(APIModel):
    """A course in a listing."""

    slug: str
    title: str
    subtitle: str | None
    description: str
    level: str
    estimated_hours: int
    outcomes: list[str]
    module_count: int
    lesson_count: int


class CourseDetail(CourseSummary):
    """A course with its module tree."""

    modules: list[ModuleSummary]


class LessonProgressResponse(APIModel):
    """A learner's state on one lesson."""

    status: str
    view_count: int
    exercises_completed: int
    exercises_total: int
    time_spent_seconds: int
    scratch_files: dict[str, str]
    notes: str
    completed_at: datetime | None


class SaveScratchRequest(APIModel):
    """Autosave payload for a lesson's editor."""

    files: dict[str, str]
    notes: Annotated[str | None, Field(max_length=20000)] = None


class RecordTimeRequest(APIModel):
    """Time-on-task report from the client."""

    seconds: Annotated[int, Field(ge=0, le=3600)]


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------


class ExerciseSummary(APIModel):
    """An exercise in a listing."""

    slug: str
    title: str
    kind: str
    level: str
    difficulty: float
    estimated_minutes: int
    xp_reward: int
    position: int
    is_challenge: bool
    challenge_kind: str | None
    status: str = "not_attempted"
    best_score: float = 0.0


class HintResponse(APIModel):
    """One unlocked hint rung."""

    level: int
    text: str
    penalty: float
    is_last: bool


class ExecutionPlan(APIModel):
    """How to run this exercise, for clients that execute code themselves.

    Populated only when the server has no sandbox of its own
    (``PYFORGE_EXECUTOR=client``). ``extra_files`` carries the exercise's hidden
    test suite, which the browser cannot run without — so on a client-executed
    deployment the "hidden" tests are readable by anyone who opens devtools.
    That is inherent to running the grader on the learner's machine.
    """

    mode: str = Field(description='"script" or "pytest".')
    entrypoint: str = "main.py"
    stdin: str = ""
    pytest_args: list[str] = Field(default_factory=list)
    extra_files: dict[str, str] = Field(
        default_factory=dict, description="Hidden test files merged in before the run."
    )
    timeout_seconds: float = 10.0


class ExerciseDetail(APIModel):
    """Everything needed to attempt an exercise.

    The reference solution is deliberately absent: it is served only by its own
    gated endpoint. Hidden test files are absent too, *unless* the deployment
    executes code client-side, in which case they must travel with
    ``execution_plan`` — see :class:`ExecutionPlan`.
    """

    slug: str
    title: str
    prompt: str
    kind: str
    level: str
    difficulty: float
    estimated_minutes: int
    xp_reward: int
    starter_files: dict[str, str]
    grader: str
    concept_slugs: list[str]
    lesson_slug: str | None
    hint_count: int
    hints_revealed: int
    solution_unlocked: bool
    time_limit_minutes: int | None
    attempts: int
    best_score: float
    status: str
    #: Multiple-choice options, when the grader needs them.
    options: list[str] | None = None
    #: Present only when the client is expected to run the code itself.
    execution_plan: ExecutionPlan | None = None


class SolutionResponse(APIModel):
    """A revealed reference solution."""

    files: dict[str, str]
    explanation: str


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class ClientExecutionResult(APIModel):
    """A run the client performed itself, reported back for grading.

    When ``PYFORGE_EXECUTOR=client`` the sandbox is the learner's own browser
    (Pyodide/WASM), so the server never runs the code and instead grades the
    output the client reports. This is trusted input: a learner can forge a pass.
    That is an accepted trade for a deployment with no server-side sandbox — the
    only person they can cheat is themselves — but it means these values must
    never be used for anything but this learner's own progress.
    """

    exit_code: int = 1
    stdout: Annotated[str, Field(max_length=200_000)] = ""
    stderr: Annotated[str, Field(max_length=200_000)] = ""
    timed_out: bool = False
    duration_ms: Annotated[int, Field(ge=0, le=600_000)] = 0
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class ExecuteRequest(APIModel):
    """Run arbitrary code in the sandbox."""

    files: dict[str, str] = Field(description="Relative path → file contents.")
    entrypoint: Annotated[str, Field(max_length=200)] = "main.py"
    mode: ExecutionMode = ExecutionMode.SCRIPT
    stdin: Annotated[str, Field(max_length=65536)] = ""
    lesson_slug: str | None = None
    exercise_slug: str | None = None
    execution: ClientExecutionResult | None = Field(
        default=None,
        description="Result of running the code client-side. Recorded instead of "
        "running the sandbox when the server has none; ignored when it does.",
    )


class ExecuteResponse(APIModel):
    """The result of a sandbox run."""

    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int
    stdout_truncated: bool
    stderr_truncated: bool
    error: str | None = None
    #: Plain-language reading of any traceback, from the same engine the grader uses.
    error_explanation: str | None = None


class ExecutionHealthResponse(APIModel):
    """Execution engine status."""

    backend: str
    healthy: bool
    isolated: bool
    timeout_seconds: float
    memory_mb: int
    max_files: int


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------


class SubmitRequest(APIModel):
    """Submit an exercise attempt."""

    files: dict[str, str] = Field(default_factory=dict)
    selected_index: int | None = Field(
        default=None, description="Chosen option for multiple-choice exercises."
    )
    time_spent_seconds: Annotated[int, Field(ge=0, le=86400)] = 0
    execution: ClientExecutionResult | None = Field(
        default=None,
        description="Result of running the code client-side. Required when the "
        "server has no sandbox; ignored when it does.",
    )


class CheckResponse(APIModel):
    """One graded criterion."""

    name: str
    passed: bool
    message: str
    expected: str | None = None
    actual: str | None = None
    diff: str | None = None


class MasteryDelta(APIModel):
    """How one concept's mastery moved."""

    concept_slug: str
    concept_name: str
    previous: float
    current: float
    delta: float
    band: str


class SubmissionResponse(APIModel):
    """The verdict on one attempt."""

    id: str
    exercise_slug: str
    attempt_number: int
    status: str
    score: float
    checks: list[CheckResponse]
    feedback: str
    stdout: str
    stderr: str
    duration_ms: int
    hints_used: int
    xp_awarded: int
    mastery_deltas: list[MasteryDelta]
    newly_earned_achievements: list[str]
    created_at: datetime


class SubmissionHistoryItem(APIModel):
    """A past attempt in the history panel."""

    id: str
    attempt_number: int
    status: str
    score: float
    created_at: datetime
    hints_used: int


# ---------------------------------------------------------------------------
# Mastery / progress
# ---------------------------------------------------------------------------


class MasteryItem(APIModel):
    """Decayed mastery for one concept."""

    concept_slug: str
    concept_name: str
    category: str
    level: str
    score: float
    percent: int
    confidence: float
    band: str
    attempts: int
    accuracy: float
    hints_used: int
    is_mastered: bool
    last_practiced_at: datetime | None
    top_misconceptions: list[str]


class MasteryOverview(APIModel):
    """Mastery across the curriculum."""

    overall: float
    concepts: list[MasteryItem]
    weak_areas: list[MasteryItem]
    strong_areas: list[MasteryItem]
    mastered_count: int


class RecommendationResponse(APIModel):
    """A suggested next step."""

    kind: str
    title: str
    reason: str
    lesson_slug: str | None
    exercise_slug: str | None
    concept_slug: str | None
    priority: float


class RemediationResponse(APIModel):
    """The adaptive response to repeated failure."""

    stage: str
    misconception: str | None
    misconception_label: str | None
    explanation: str
    concept_slug: str | None
    next_exercise_slug: str | None
    message: str


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class ProjectSummary(APIModel):
    """A project in the academy listing."""

    slug: str
    title: str
    tagline: str
    level: str
    guidance: str
    estimated_hours: int
    xp_reward: int
    is_capstone: bool
    concept_slugs: list[str]
    status: str = "not_started"
    best_score: float = 0.0


class ProjectDetail(ProjectSummary):
    """A project brief."""

    requirements: str
    architecture_notes: str
    suggested_structure: str
    milestones: list[dict[str, Any]]
    starter_files: dict[str, str]
    rubric: list[dict[str, Any]]
    prerequisite_slugs: list[str]
    workspace: ProjectWorkspaceResponse | None = None


class ProjectWorkspaceResponse(APIModel):
    """A learner's saved project files."""

    files: dict[str, str]
    entrypoint: str
    completed_milestones: list[str]
    notes: str
    updated_at: datetime


class SaveWorkspaceRequest(APIModel):
    """Autosave a project workspace."""

    files: dict[str, str]
    entrypoint: Annotated[str | None, Field(max_length=200)] = None
    completed_milestones: list[str] | None = None
    notes: Annotated[str | None, Field(max_length=50000)] = None


class ProjectSubmitRequest(APIModel):
    """Submit a project for evaluation."""

    files: dict[str, str]


class ProjectSubmissionResponse(APIModel):
    """A graded project submission."""

    id: str
    project_slug: str
    attempt_number: int
    verdict: str
    overall_score: float
    tests_passed: int
    tests_total: int
    rubric_scores: list[dict[str, Any]]
    review_markdown: str
    stdout: str
    stderr: str
    xp_awarded: int = 0
    created_at: datetime


# ---------------------------------------------------------------------------
# Code review
# ---------------------------------------------------------------------------


class ReviewRequest(APIModel):
    """Request a review of arbitrary files."""

    files: dict[str, str]


class FindingResponse(APIModel):
    """One review finding."""

    dimension: str
    severity: str
    message: str
    suggestion: str
    file: str
    line: int | None


class ReviewResponse(APIModel):
    """A complete code review."""

    findings: list[FindingResponse]
    dimension_scores: dict[str, float]
    overall_score: float
    summary: str
    strengths: list[str]


# ---------------------------------------------------------------------------
# AI tutor
# ---------------------------------------------------------------------------


class StartConversationRequest(APIModel):
    """Open a tutoring thread."""

    mode: AIMode = AIMode.FREEFORM
    title: Annotated[str | None, Field(max_length=200)] = None
    lesson_slug: str | None = None
    exercise_slug: str | None = None


class SendMessageRequest(APIModel):
    """Send a turn to the tutor."""

    message: Annotated[str, Field(min_length=1, max_length=8000)]
    mode: AIMode | None = None
    code: Annotated[str | None, Field(max_length=40000)] = None
    error_output: Annotated[str | None, Field(max_length=20000)] = None


class AIMessageResponse(APIModel):
    """One tutor turn."""

    id: str
    role: str
    content: str
    meta: dict[str, Any]
    created_at: datetime


class ConversationSummary(APIModel):
    """A tutoring thread in the sidebar."""

    id: str
    title: str
    mode: str
    context: dict[str, Any]
    hint_level_reached: int
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    """A thread with its messages."""

    messages: list[AIMessageResponse]


class AIStatusResponse(APIModel):
    """Whether a live model backs the tutor."""

    backend: str
    model: str | None
    live: bool
    daily_limit: int
    used_today: int


# ---------------------------------------------------------------------------
# Reference & search
# ---------------------------------------------------------------------------


class ReferenceSummary(APIModel):
    """A reference entry in a listing."""

    key: str
    title: str
    kind: str
    module: str
    signature: str
    summary: str


class ReferenceDetail(ReferenceSummary):
    """A full reference entry."""

    description: str
    parameters: list[dict[str, Any]]
    returns: str
    raises: list[dict[str, str]]
    examples: list[dict[str, Any]]
    real_world_usage: str
    common_mistakes: list[dict[str, str]]
    performance_notes: str
    security_notes: str
    related_keys: list[str]
    exercise_slugs: list[str]
    lesson_slugs: list[str]


class SearchHitResponse(APIModel):
    """One global-search result."""

    kind: str
    slug: str
    title: str
    snippet: str
    score: float
    url: str
    meta: dict[str, Any]


class SearchResponse(APIModel):
    """Global-search results."""

    query: str
    total: int
    hits: list[SearchHitResponse]


# ---------------------------------------------------------------------------
# Interview & challenges
# ---------------------------------------------------------------------------


class QuizQuestionResponse(APIModel):
    """An interview or concept-check question, without the answer."""

    slug: str
    question: str
    code_snippet: str | None
    options: list[str]
    category: str
    level: str
    tracks: list[str]


class QuizAnswerRequest(APIModel):
    """Answer to a quiz question."""

    slug: str
    selected_index: int


class QuizAnswerResponse(APIModel):
    """Whether the answer was right, and why."""

    correct: bool
    correct_index: int
    explanation: str


class ChallengeSummary(ExerciseSummary):
    """A challenge in the challenge listing."""

    time_limit_minutes: int | None = None
    prompt: str = ""


# ---------------------------------------------------------------------------
# Certification & achievements
# ---------------------------------------------------------------------------


class CertificationStatusResponse(APIModel):
    """Progress toward one certification."""

    level: str
    title: str
    description: str
    earned: bool
    eligible: bool
    progress: float
    unmet_requirements: list[str]
    evidence: dict[str, Any]
    awarded_at: str | None
    certificate_code: str | None


class AchievementResponse(APIModel):
    """A badge, earned or not."""

    slug: str
    name: str
    description: str
    icon: str
    tier: str
    xp_reward: int
    earned: bool
    earned_at: datetime | None


# Resolve forward references declared before their targets.
LessonDetail.model_rebuild()
ProjectDetail.model_rebuild()
