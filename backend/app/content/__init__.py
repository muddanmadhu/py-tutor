"""Seed curriculum content.

Content is authored as typed dataclasses (see :mod:`app.content.schema`) and
validated at import time, so a malformed lesson is a startup failure rather than
a mystery in production.

Adding content means adding a :class:`~app.content.schema.LessonSpec` to a
module and re-running the seeder — no code changes anywhere else. See
``docs/CURRICULUM.md``.
"""

from __future__ import annotations

from app.content.achievements import ACHIEVEMENTS, QUIZ_BANK
from app.content.concepts import CONCEPTS
from app.content.lessons import CORE_MODULE, FOUNDATIONS_MODULE, PROFESSIONAL_MODULE
from app.content.projects import PROJECTS
from app.content.reference_entries import REFERENCE
from app.content.schema import CourseSpec, validate
from app.models.enums import SkillLevel

MASTERY_COURSE = CourseSpec(
    slug="python-engineering-mastery",
    title="Python Engineering Mastery",
    subtitle="From your first line of code to a production Python service",
    description="""\
A single path from absolute beginner to production-ready Python engineer.

You will not read your way through this. Every lesson ends in code you write and
run, every concept is assessed against real execution, and the final assessment
is a business requirement document rather than a multiple-choice test.

The path deliberately front-loads the ideas that everything else depends on —
the execution model, names and objects, functions — then broadens into
collections, error handling, objects, files, HTTP, testing and unattended
automation. It closes with four projects whose scaffolding fades until you are
handed nothing but requirements.""",
    level=SkillLevel.BEGINNER,
    estimated_hours=60,
    outcomes=(
        "Write, run and debug Python programs with confidence",
        "Choose the right data structure and justify the choice",
        "Design functions and classes that other people can read and test",
        "Handle failure deliberately, so problems are visible rather than silent",
        "Read and write files, JSON and CSV without losing data",
        "Consume HTTP APIs resiliently: timeouts, retries, pagination, auth",
        "Write test suites that catch real defects and survive refactoring",
        "Build automation that runs unattended and can be diagnosed from its logs",
        "Take a business requirement and deliver a designed, tested, deployable service",
    ),
    modules=(FOUNDATIONS_MODULE, CORE_MODULE, PROFESSIONAL_MODULE),
)

COURSES: tuple[CourseSpec, ...] = (MASTERY_COURSE,)

# Fail at import time rather than at seed time in production.
validate(COURSES, CONCEPTS, PROJECTS)

__all__ = [
    "ACHIEVEMENTS",
    "CONCEPTS",
    "COURSES",
    "MASTERY_COURSE",
    "PROJECTS",
    "QUIZ_BANK",
    "REFERENCE",
]
