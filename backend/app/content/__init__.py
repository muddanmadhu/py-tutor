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
from app.content.lessons import (
    ALGORITHMS_MODULE,
    CORE_MODULE,
    FOUNDATIONS_MODULE,
    PROFESSIONAL_MODULE,
)
from app.content.projects import CALCULATOR, CAPSTONE, EXPENSE_TRACKER, FILE_PLATFORM
from app.content.projects_realworld import (
    API_CLIENT_SDK,
    CSV_REPORT_ENGINE,
    ETL_PIPELINE,
    INCIDENT_REPORT,
    INVENTORY_SYNC,
    INVOICE_RECONCILIATION,
    LOG_ANALYZER,
)
from app.content.reference_entries import REFERENCE as SEED_REFERENCE
from app.content.reference_stdlib import ADDITIONAL_REFERENCE
from app.content.schema import CourseSpec, ModuleSpec, ProjectSpec, validate
from app.models.enums import SkillLevel

#: The Python Reference library. Split across two modules purely for file size.
REFERENCE = SEED_REFERENCE + ADDITIONAL_REFERENCE

#: The project ladder, in the order a learner meets it. Ordered so every project's
#: prerequisites appear before it, and so guidance fades monotonically:
#: fully guided -> partially guided -> requirements only -> independent.
PROJECTS: tuple[ProjectSpec, ...] = (
    CALCULATOR,
    EXPENSE_TRACKER,
    LOG_ANALYZER,
    CSV_REPORT_ENGINE,
    API_CLIENT_SDK,
    INVOICE_RECONCILIATION,
    ETL_PIPELINE,
    INVENTORY_SYNC,
    FILE_PLATFORM,
    INCIDENT_REPORT,
    CAPSTONE,
)

_MODULES: tuple[ModuleSpec, ...] = (
    FOUNDATIONS_MODULE,
    ALGORITHMS_MODULE,
    CORE_MODULE,
    PROFESSIONAL_MODULE,
)


def _estimated_hours(modules: tuple[ModuleSpec, ...], projects: tuple[ProjectSpec, ...]) -> int:
    """Total learner hours, derived from the content rather than declared.

    This was a hand-written literal, which is a number that is correct only until
    the next content change — and an audit found it had to be reverse-engineered
    to know whether it still was. The three sources are all here, so compute it.

    Lesson and exercise time are separate fields: a lesson's ``estimated_minutes``
    covers the teaching material only, and each exercise carries its own estimate.
    """
    minutes = sum(lesson.estimated_minutes for module in modules for lesson in module.lessons)
    minutes += sum(
        exercise.estimated_minutes
        for module in modules
        for lesson in module.lessons
        for exercise in lesson.exercises
    )
    return round(minutes / 60 + sum(project.estimated_hours for project in projects))


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
    estimated_hours=_estimated_hours(_MODULES, PROJECTS),
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
    modules=_MODULES,
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
