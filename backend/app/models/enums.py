"""Enumerations shared across models, schemas and services.

Stored as short strings rather than native database enums: adding a value is
then a code change, not a migration, which matters for a curriculum that grows
continuously.
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    """Authorisation role."""

    LEARNER = "learner"
    AUTHOR = "author"
    ADMIN = "admin"


class SkillLevel(StrEnum):
    """Curriculum difficulty tier (mirrors the five learner levels)."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"
    ENGINEERING = "engineering"


class ExerciseKind(StrEnum):
    """What the learner is asked to do."""

    CODE = "code"
    """Write code that produces a required result."""

    DEBUG = "debug"
    """Given broken code, find and fix the defect."""

    TEST_WRITING = "test_writing"
    """Given an implementation, write tests that catch the bug."""

    PREDICT_OUTPUT = "predict_output"
    """Reason about code without running it."""

    QUIZ = "quiz"
    """Multiple-choice concept check."""

    REFACTOR = "refactor"
    """Improve working code against quality criteria."""

    PROJECT = "project"
    """Multi-file build assessed against a rubric."""


class GraderKind(StrEnum):
    """How a submission is judged."""

    STDOUT_MATCH = "stdout_match"
    PYTEST = "pytest"
    STATIC_ASSERT = "static_assert"
    MULTIPLE_CHOICE = "multiple_choice"
    RUBRIC = "rubric"


class SubmissionStatus(StrEnum):
    """Outcome of a graded submission."""

    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    ERROR = "error"
    TIMED_OUT = "timed_out"


class ExecutionMode(StrEnum):
    """Which entrypoint the sandbox uses."""

    SCRIPT = "script"
    PYTEST = "pytest"


class GuidanceLevel(StrEnum):
    """How much scaffolding a project provides (section 50 of the spec)."""

    FULLY_GUIDED = "fully_guided"
    PARTIALLY_GUIDED = "partially_guided"
    REQUIREMENTS_ONLY = "requirements_only"
    INDEPENDENT = "independent"


class ChallengeKind(StrEnum):
    """Challenge format."""

    QUICK = "quick"
    CODING = "coding"
    DEBUGGING = "debugging"
    ALGORITHM = "algorithm"
    REAL_WORLD = "real_world"
    PROJECT = "project"


class LearningEventKind(StrEnum):
    """Analytics event types."""

    LESSON_VIEWED = "lesson_viewed"
    LESSON_COMPLETED = "lesson_completed"
    CODE_EXECUTED = "code_executed"
    SUBMISSION_GRADED = "submission_graded"
    HINT_REVEALED = "hint_revealed"
    SOLUTION_VIEWED = "solution_viewed"
    PROJECT_STARTED = "project_started"
    PROJECT_SUBMITTED = "project_submitted"
    AI_MESSAGE_SENT = "ai_message_sent"
    CERTIFICATION_EARNED = "certification_earned"


class AIMode(StrEnum):
    """Which tutoring behaviour the AI adopts."""

    EXPLAIN_CODE = "explain_code"
    EXPLAIN_ERROR = "explain_error"
    HINT = "hint"
    SOCRATIC = "socratic"
    REVIEW = "review"
    GENERATE_EXERCISE = "generate_exercise"
    GENERATE_TESTS = "generate_tests"
    MOCK_INTERVIEW = "mock_interview"
    FREEFORM = "freeform"


class CertificationLevel(StrEnum):
    """Certification tracks (section 52 of the spec)."""

    FOUNDATIONS = "python_foundations"
    DEVELOPER = "python_developer"
    ADVANCED_DEVELOPER = "advanced_python_developer"
    AUTOMATION_ENGINEER = "python_automation_engineer"
    BACKEND_DEVELOPER = "python_backend_developer"
    TEST_AUTOMATION_ENGINEER = "python_test_automation_engineer"
    ENGINEERING_MASTER = "python_engineering_master"
