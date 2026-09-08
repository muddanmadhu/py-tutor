"""Authoring types for seed content.

Content is authored as plain Python dataclasses rather than YAML or JSON for
three reasons: it type-checks, it can share constants (concept slugs are
referenced, not retyped), and a malformed lesson fails at import rather than at
seed time in production.

:func:`validate` enforces the content-quality checklist from the specification —
a lesson that does not answer *why does it exist*, *when should I not use it*,
*what are the common mistakes* and the rest is rejected, so the standard is
mechanical rather than aspirational.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.enums import (
    ChallengeKind,
    ExerciseKind,
    GraderKind,
    GuidanceLevel,
    SkillLevel,
)

#: Sections every lesson must provide (spec §49).
REQUIRED_SECTIONS = (
    "what_is_it",
    "why_it_exists",
    "how_it_works",
    "when_to_use",
    "when_not_to_use",
    "common_mistakes",
    "real_world",
    "alternatives",
    "performance",
    "security",
)


class ContentError(Exception):
    """A seed content definition is invalid."""


@dataclass(frozen=True, slots=True)
class ConceptSpec:
    """A masterable concept."""

    slug: str
    name: str
    description: str
    category: str
    level: SkillLevel = SkillLevel.BEGINNER
    difficulty: float = 0.5
    weight: float = 1.0
    prerequisites: tuple[str, ...] = ()
    misconceptions: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Example:
    """A worked example inside a lesson."""

    title: str
    code: str
    output: str = ""
    explanation: str = ""

    def to_dict(self) -> dict[str, str]:
        """Serialise for storage."""
        return {
            "title": self.title,
            "code": self.code.strip("\n"),
            "output": self.output.strip("\n"),
            "explanation": self.explanation.strip(),
        }


@dataclass(frozen=True, slots=True)
class HintSpec:
    """One rung of the hint ladder."""

    text: str
    penalty: float = 0.05


@dataclass(frozen=True, slots=True)
class ExerciseSpec:
    """A gradeable task."""

    slug: str
    title: str
    prompt: str
    kind: ExerciseKind = ExerciseKind.CODE
    level: SkillLevel = SkillLevel.BEGINNER
    difficulty: float = 0.4
    estimated_minutes: int = 8
    xp_reward: int = 25
    starter_files: dict[str, str] = field(default_factory=dict)
    hidden_files: dict[str, str] = field(default_factory=dict)
    solution_files: dict[str, str] = field(default_factory=dict)
    solution_explanation: str = ""
    grader: GraderKind = GraderKind.PYTEST
    grader_config: dict[str, Any] = field(default_factory=dict)
    concepts: tuple[str, ...] = ()
    hints: tuple[HintSpec, ...] = ()
    misconception_rules: tuple[dict[str, str], ...] = ()
    is_challenge: bool = False
    challenge_kind: ChallengeKind | None = None
    time_limit_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class LessonSpec:
    """A unit of instruction."""

    slug: str
    title: str
    summary: str
    body: str
    sections: dict[str, str]
    level: SkillLevel = SkillLevel.BEGINNER
    estimated_minutes: int = 15
    xp_reward: int = 20
    starter_code: str = ""
    examples: tuple[Example, ...] = ()
    visualizations: tuple[dict[str, Any], ...] = ()
    concepts: tuple[str, ...] = ()
    reference_keys: tuple[str, ...] = ()
    exercises: tuple[ExerciseSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class ModuleSpec:
    """A themed group of lessons."""

    slug: str
    title: str
    summary: str
    level: SkillLevel
    lessons: tuple[LessonSpec, ...]


@dataclass(frozen=True, slots=True)
class CourseSpec:
    """A learning path."""

    slug: str
    title: str
    subtitle: str
    description: str
    level: SkillLevel
    outcomes: tuple[str, ...]
    estimated_hours: int
    modules: tuple[ModuleSpec, ...]


@dataclass(frozen=True, slots=True)
class ProjectSpec:
    """A project academy build."""

    slug: str
    title: str
    tagline: str
    level: SkillLevel
    guidance: GuidanceLevel
    estimated_hours: int
    xp_reward: int
    requirements: str
    architecture_notes: str = ""
    suggested_structure: str = ""
    milestones: tuple[dict[str, Any], ...] = ()
    starter_files: dict[str, str] = field(default_factory=dict)
    acceptance_tests: dict[str, str] = field(default_factory=dict)
    rubric: tuple[dict[str, Any], ...] = ()
    concepts: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    is_capstone: bool = False


@dataclass(frozen=True, slots=True)
class ReferenceSpec:
    """A Python reference entry."""

    key: str
    title: str
    kind: str
    module: str
    signature: str
    summary: str
    description: str = ""
    parameters: tuple[dict[str, Any], ...] = ()
    returns: str = ""
    raises: tuple[dict[str, str], ...] = ()
    examples: tuple[dict[str, str], ...] = ()
    real_world_usage: str = ""
    common_mistakes: tuple[dict[str, str], ...] = ()
    performance_notes: str = ""
    security_notes: str = ""
    related: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    lesson_slugs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AchievementSpec:
    """A badge definition."""

    slug: str
    name: str
    description: str
    icon: str
    tier: str
    xp_reward: int
    criteria: dict[str, Any]


@dataclass(frozen=True, slots=True)
class QuizSpec:
    """An interview or concept-check question."""

    slug: str
    question: str
    options: tuple[str, ...]
    correct_index: int
    explanation: str
    category: str
    level: SkillLevel
    tracks: tuple[str, ...] = ()
    code_snippet: str | None = None
    concepts: tuple[str, ...] = ()


def validate(
    courses: tuple[CourseSpec, ...],
    concepts: tuple[ConceptSpec, ...],
    projects: tuple[ProjectSpec, ...],
) -> None:
    """Check content integrity before it reaches the database.

    Raises
    ------
    ContentError
        On a duplicate slug, an unknown concept reference, a missing required
        lesson section, or an exercise whose grader is not configured.
    """
    concept_slugs = {concept.slug for concept in concepts}
    if len(concept_slugs) != len(concepts):
        raise ContentError("duplicate concept slugs")

    for concept in concepts:
        unknown = set(concept.prerequisites) - concept_slugs
        if unknown:
            raise ContentError(f"concept '{concept.slug}' requires unknown {sorted(unknown)}")

    lesson_slugs: set[str] = set()
    exercise_slugs: set[str] = set()

    for course in courses:
        for module in course.modules:
            for lesson in module.lessons:
                if lesson.slug in lesson_slugs:
                    raise ContentError(f"duplicate lesson slug: {lesson.slug}")
                lesson_slugs.add(lesson.slug)

                missing = [key for key in REQUIRED_SECTIONS if not lesson.sections.get(key)]
                if missing:
                    raise ContentError(
                        f"lesson '{lesson.slug}' is missing required sections: {missing}"
                    )
                unknown = set(lesson.concepts) - concept_slugs
                if unknown:
                    raise ContentError(
                        f"lesson '{lesson.slug}' references unknown concepts {sorted(unknown)}"
                    )

                for exercise in lesson.exercises:
                    if exercise.slug in exercise_slugs:
                        raise ContentError(f"duplicate exercise slug: {exercise.slug}")
                    exercise_slugs.add(exercise.slug)
                    _validate_exercise(exercise, concept_slugs)

    for project in projects:
        unknown = set(project.concepts) - concept_slugs
        if unknown:
            raise ContentError(
                f"project '{project.slug}' references unknown concepts {sorted(unknown)}"
            )
        if not project.rubric:
            raise ContentError(f"project '{project.slug}' has no rubric")


def _validate_exercise(exercise: ExerciseSpec, concept_slugs: set[str]) -> None:
    unknown = set(exercise.concepts) - concept_slugs
    if unknown:
        raise ContentError(
            f"exercise '{exercise.slug}' references unknown concepts {sorted(unknown)}"
        )
    if not exercise.concepts:
        raise ContentError(f"exercise '{exercise.slug}' assesses no concept")

    if exercise.grader is GraderKind.PYTEST and not exercise.hidden_files:
        raise ContentError(f"pytest exercise '{exercise.slug}' has no hidden test files")
    if exercise.grader is GraderKind.STDOUT_MATCH and not exercise.grader_config.get(
        "expected_stdout"
    ):
        raise ContentError(f"stdout exercise '{exercise.slug}' has no expected output")
    if exercise.grader is GraderKind.STATIC_ASSERT and not exercise.grader_config.get("assertions"):
        raise ContentError(f"static exercise '{exercise.slug}' has no assertions")
    if exercise.grader is GraderKind.MULTIPLE_CHOICE:
        options = exercise.grader_config.get("options", [])
        index = exercise.grader_config.get("correct_index", -1)
        if not options or not 0 <= int(index) < len(options):
            raise ContentError(f"quiz exercise '{exercise.slug}' has an invalid answer key")
    if exercise.kind is not ExerciseKind.QUIZ and not exercise.hints:
        raise ContentError(f"exercise '{exercise.slug}' has no hint ladder")
