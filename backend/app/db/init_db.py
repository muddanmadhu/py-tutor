"""Database bootstrap and content seeding.

Run as a module:

    python -m app.db.init_db --seed          # create tables and load content
    python -m app.db.init_db --seed --demo   # also create a demo learner
    python -m app.db.init_db --drop --seed   # rebuild from scratch (destructive)

Seeding is **idempotent**: it upserts by slug, so re-running after editing a
lesson updates it in place rather than duplicating it. Learner progress is
keyed on database ids that the upsert preserves, so re-seeding never destroys
someone's work.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content import ACHIEVEMENTS, CONCEPTS, COURSES, PROJECTS, QUIZ_BANK, REFERENCE
from app.content.schema import (
    AchievementSpec,
    ConceptSpec,
    CourseSpec,
    ExerciseSpec,
    LessonSpec,
    ProjectSpec,
    QuizSpec,
    ReferenceSpec,
)
from app.core.logging import configure_logging, get_logger
from app.db.base import Base
from app.db.session import get_engine, session_scope
from app.models import (
    Achievement,
    Concept,
    Course,
    Exercise,
    Hint,
    Lesson,
    Module,
    Project,
    QuizQuestion,
    ReferenceEntry,
)
from app.models.enums import SkillLevel, UserRole

logger = get_logger(__name__)


def create_tables() -> None:
    """Create every table that does not yet exist.

    Fine for local development and tests. Production uses Alembic — see
    ``docs/DEPLOYMENT.md``.
    """
    # Importing app.models registers every mapper on Base.metadata.
    Base.metadata.create_all(bind=get_engine())
    logger.info("database tables ensured")


def drop_tables() -> None:
    """Drop every table. Destructive; development only."""
    Base.metadata.drop_all(bind=get_engine())
    logger.warning("all database tables dropped")


def _upsert(
    session: Session, model: type[Any], *, slug_field: str, slug: str, **values: Any
) -> Any:
    """Fetch by natural key and update, or create. Returns the persisted instance.

    Typed loosely on purpose: this is a generic upsert over heterogeneous models
    with different constructors, and pretending otherwise would mean a cast at
    every call site.
    """
    column = getattr(model, slug_field)
    instance = session.scalar(select(model).where(column == slug))
    if instance is None:
        instance = model(**{slug_field: slug}, **values)
        session.add(instance)
    else:
        for key, value in values.items():
            setattr(instance, key, value)
    session.flush()
    return instance


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def seed_concepts(session: Session, specs: tuple[ConceptSpec, ...]) -> dict[str, Concept]:
    """Insert concepts, then wire up the prerequisite graph in a second pass."""
    by_slug: dict[str, Concept] = {}
    for spec in specs:
        by_slug[spec.slug] = _upsert(
            session,
            Concept,
            slug_field="slug",
            slug=spec.slug,
            name=spec.name,
            description=spec.description,
            level=spec.level.value,
            category=spec.category,
            difficulty=spec.difficulty,
            weight=spec.weight,
            common_misconceptions=[dict(item) for item in spec.misconceptions],
        )

    # Second pass: every concept now exists, so edges can be resolved.
    for spec in specs:
        concept = by_slug[spec.slug]
        concept.prerequisites = [by_slug[slug] for slug in spec.prerequisites]
    session.flush()
    logger.info("seeded %d concepts", len(by_slug))
    return by_slug


def seed_courses(
    session: Session, specs: tuple[CourseSpec, ...], concepts: dict[str, Concept]
) -> None:
    """Insert courses, modules, lessons, exercises and hints."""
    lesson_count = exercise_count = 0

    for course_position, course_spec in enumerate(specs):
        course = _upsert(
            session,
            Course,
            slug_field="slug",
            slug=course_spec.slug,
            title=course_spec.title,
            subtitle=course_spec.subtitle,
            description=course_spec.description,
            level=course_spec.level.value,
            position=course_position,
            outcomes=list(course_spec.outcomes),
            estimated_hours=course_spec.estimated_hours,
            is_published=True,
        )

        for module_position, module_spec in enumerate(course_spec.modules):
            module = session.scalar(
                select(Module).where(Module.course_id == course.id, Module.slug == module_spec.slug)
            )
            if module is None:
                module = Module(course_id=course.id, slug=module_spec.slug)
                session.add(module)
            module.title = module_spec.title
            module.summary = module_spec.summary
            module.level = module_spec.level.value
            module.position = module_position
            module.estimated_minutes = sum(
                lesson.estimated_minutes for lesson in module_spec.lessons
            )
            session.flush()

            for lesson_position, lesson_spec in enumerate(module_spec.lessons):
                _seed_lesson(
                    session, module, lesson_spec, lesson_position, concepts, course_position
                )
                lesson_count += 1
                exercise_count += len(lesson_spec.exercises)

    logger.info("seeded %d lessons and %d exercises", lesson_count, exercise_count)


def _seed_lesson(
    session: Session,
    module: Module,
    spec: LessonSpec,
    position: int,
    concepts: dict[str, Concept],
    course_position: int,
) -> Lesson:
    lesson = session.scalar(select(Lesson).where(Lesson.slug == spec.slug))
    if lesson is None:
        lesson = Lesson(slug=spec.slug, module_id=module.id)
        session.add(lesson)
    lesson.module_id = module.id
    lesson.title = spec.title
    lesson.summary = spec.summary
    lesson.level = spec.level.value
    # Global ordering: course, then module, then lesson.
    lesson.position = course_position * 10_000 + module.position * 100 + position
    lesson.estimated_minutes = spec.estimated_minutes
    lesson.body = spec.body
    lesson.sections = dict(spec.sections)
    lesson.starter_code = spec.starter_code
    lesson.examples = [example.to_dict() for example in spec.examples]
    lesson.visualizations = [dict(item) for item in spec.visualizations]
    lesson.reference_keys = list(spec.reference_keys)
    lesson.xp_reward = spec.xp_reward
    lesson.concepts = [concepts[slug] for slug in spec.concepts if slug in concepts]
    session.flush()

    for exercise_position, exercise_spec in enumerate(spec.exercises):
        _seed_exercise(session, lesson, exercise_spec, exercise_position)
    return lesson


def _seed_exercise(session: Session, lesson: Lesson, spec: ExerciseSpec, position: int) -> Exercise:
    exercise = session.scalar(select(Exercise).where(Exercise.slug == spec.slug))
    if exercise is None:
        exercise = Exercise(slug=spec.slug, lesson_id=lesson.id)
        session.add(exercise)
    exercise.lesson_id = lesson.id
    exercise.title = spec.title
    exercise.prompt = spec.prompt
    exercise.kind = spec.kind.value
    exercise.level = spec.level.value
    exercise.position = position
    exercise.difficulty = spec.difficulty
    exercise.estimated_minutes = spec.estimated_minutes
    exercise.xp_reward = spec.xp_reward
    exercise.starter_files = dict(spec.starter_files)
    exercise.hidden_files = dict(spec.hidden_files)
    exercise.solution_files = dict(spec.solution_files)
    exercise.solution_explanation = spec.solution_explanation
    exercise.grader = spec.grader.value
    exercise.grader_config = dict(spec.grader_config)
    exercise.concept_slugs = list(spec.concepts)
    exercise.misconception_rules = [dict(rule) for rule in spec.misconception_rules]
    exercise.is_challenge = spec.is_challenge
    exercise.challenge_kind = spec.challenge_kind.value if spec.challenge_kind else None
    exercise.time_limit_minutes = spec.time_limit_minutes
    session.flush()

    # Replace the hint ladder wholesale: authored hints are content, not user data.
    for existing in list(exercise.hints):
        session.delete(existing)
    session.flush()
    for level, hint_spec in enumerate(spec.hints, start=1):
        session.add(
            Hint(
                exercise_id=exercise.id,
                level=level,
                text=hint_spec.text,
                penalty=hint_spec.penalty,
            )
        )
    session.flush()
    return exercise


def seed_projects(session: Session, specs: tuple[ProjectSpec, ...]) -> None:
    """Insert the project academy catalogue."""
    for position, spec in enumerate(specs):
        _upsert(
            session,
            Project,
            slug_field="slug",
            slug=spec.slug,
            title=spec.title,
            tagline=spec.tagline,
            level=spec.level.value,
            guidance=spec.guidance.value,
            position=position,
            estimated_hours=spec.estimated_hours,
            xp_reward=spec.xp_reward,
            is_capstone=spec.is_capstone,
            requirements=spec.requirements,
            architecture_notes=spec.architecture_notes,
            suggested_structure=spec.suggested_structure,
            milestones=[dict(item) for item in spec.milestones],
            starter_files=dict(spec.starter_files),
            acceptance_tests=dict(spec.acceptance_tests),
            rubric=[dict(item) for item in spec.rubric],
            concept_slugs=list(spec.concepts),
            prerequisite_slugs=list(spec.prerequisites),
        )
    logger.info("seeded %d projects", len(specs))


def seed_reference(session: Session, specs: tuple[ReferenceSpec, ...]) -> None:
    """Insert the Python reference."""
    for spec in specs:
        _upsert(
            session,
            ReferenceEntry,
            slug_field="key",
            slug=spec.key,
            title=spec.title,
            kind=spec.kind,
            module=spec.module,
            signature=spec.signature,
            summary=spec.summary,
            description=spec.description,
            parameters=[dict(item) for item in spec.parameters],
            returns=spec.returns,
            raises=[dict(item) for item in spec.raises],
            examples=[dict(item) for item in spec.examples],
            real_world_usage=spec.real_world_usage,
            common_mistakes=[dict(item) for item in spec.common_mistakes],
            performance_notes=spec.performance_notes,
            security_notes=spec.security_notes,
            related_keys=list(spec.related),
            exercise_slugs=[],
            lesson_slugs=list(spec.lesson_slugs),
            keywords=list(spec.keywords),
        )
    logger.info("seeded %d reference entries", len(specs))


def seed_achievements(session: Session, specs: tuple[AchievementSpec, ...]) -> None:
    """Insert badge definitions."""
    for spec in specs:
        _upsert(
            session,
            Achievement,
            slug_field="slug",
            slug=spec.slug,
            name=spec.name,
            description=spec.description,
            icon=spec.icon,
            tier=spec.tier,
            xp_reward=spec.xp_reward,
            criteria=dict(spec.criteria),
        )
    logger.info("seeded %d achievements", len(specs))


def seed_quiz_bank(session: Session, specs: tuple[QuizSpec, ...]) -> None:
    """Insert the interview question bank."""
    for spec in specs:
        _upsert(
            session,
            QuizQuestion,
            slug_field="slug",
            slug=spec.slug,
            question=spec.question,
            code_snippet=spec.code_snippet,
            options=list(spec.options),
            correct_index=spec.correct_index,
            explanation=spec.explanation,
            category=spec.category,
            level=spec.level.value,
            concept_slugs=list(spec.concepts),
            tracks=list(spec.tracks),
        )
    logger.info("seeded %d interview questions", len(specs))


def seed_all(session: Session) -> dict[str, int]:
    """Load every piece of seed content. Idempotent."""
    concepts = seed_concepts(session, CONCEPTS)
    seed_courses(session, COURSES, concepts)
    seed_projects(session, PROJECTS)
    seed_reference(session, REFERENCE)
    seed_achievements(session, ACHIEVEMENTS)
    seed_quiz_bank(session, QUIZ_BANK)

    counts = {
        "concepts": len(CONCEPTS),
        "courses": len(COURSES),
        "lessons": sum(len(module.lessons) for course in COURSES for module in course.modules),
        "exercises": sum(
            len(lesson.exercises)
            for course in COURSES
            for module in course.modules
            for lesson in module.lessons
        ),
        "projects": len(PROJECTS),
        "reference_entries": len(REFERENCE),
        "achievements": len(ACHIEVEMENTS),
        "quiz_questions": len(QUIZ_BANK),
    }
    logger.info("seed complete", extra=counts)
    return counts


def create_demo_user(session: Session) -> None:
    """Create a demo learner for local exploration. Never run in production."""
    from app.core.security import hash_password
    from app.models import User

    email = "learner@example.com"
    if session.scalar(select(User).where(User.email == email)):
        logger.info("demo user already exists")
        return
    session.add(
        User(
            email=email,
            display_name="Demo Learner",
            password_hash=hash_password("demo-password-123"),
            role=UserRole.LEARNER.value,
            declared_level=SkillLevel.BEGINNER.value,
            goal="Become a production-ready Python engineer",
            active_course_slug=COURSES[0].slug,
        )
    )
    session.flush()
    logger.warning("demo user created: %s / demo-password-123", email)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="PyForge database bootstrap")
    parser.add_argument("--drop", action="store_true", help="drop all tables first (destructive)")
    parser.add_argument("--seed", action="store_true", help="load the seed curriculum")
    parser.add_argument("--demo", action="store_true", help="create a demo learner account")
    args = parser.parse_args(argv)

    configure_logging()

    from app.core.config import get_settings

    settings = get_settings()
    if args.drop and settings.is_production:
        logger.error("refusing to drop tables in production")
        return 1
    if args.demo and settings.is_production:
        logger.error("refusing to create a demo user in production")
        return 1

    if args.drop:
        drop_tables()
    create_tables()

    if args.seed or args.demo:
        with session_scope() as session:
            if args.seed:
                counts = seed_all(session)
                for key, value in sorted(counts.items()):
                    print(f"  {key:20} {value}")
            if args.demo:
                create_demo_user(session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
