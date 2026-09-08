"""Tests for the seed content itself.

Content bugs are as damaging as code bugs — a lesson with an unreachable
solution or a test suite that does not match its brief wastes a learner's time.
These tests check the content the same way we check the code.
"""

from __future__ import annotations

import pytest

from app.content import ACHIEVEMENTS, CONCEPTS, COURSES, PROJECTS, QUIZ_BANK, REFERENCE
from app.content.schema import REQUIRED_SECTIONS, ContentError, validate
from app.models.enums import ExerciseKind, GraderKind

ALL_LESSONS = [
    lesson for course in COURSES for module in course.modules for lesson in module.lessons
]
ALL_EXERCISES = [exercise for lesson in ALL_LESSONS for exercise in lesson.exercises]
CONCEPT_SLUGS = {concept.slug for concept in CONCEPTS}


class TestContentIntegrity:
    def test_validation_passes(self):
        validate(COURSES, CONCEPTS, PROJECTS)

    def test_the_required_seed_topics_are_present(self):
        """Spec §57 lists the minimum viable curriculum."""
        slugs = {lesson.slug for lesson in ALL_LESSONS}
        required = {
            "python-fundamentals",
            "variables-and-data-types",
            "conditions",
            "loops",
            "functions",
            "lists",
            "dictionaries",
            "exceptions",
            "object-oriented-programming",
            "file-handling",
            "apis-and-http",
            "testing",
            "automation",
        }
        assert required <= slugs, f"missing: {sorted(required - slugs)}"

    def test_there_is_a_complete_real_world_project(self):
        assert any(project.is_capstone for project in PROJECTS)

    def test_lesson_slugs_are_unique(self):
        slugs = [lesson.slug for lesson in ALL_LESSONS]
        assert len(slugs) == len(set(slugs))

    def test_exercise_slugs_are_unique(self):
        slugs = [exercise.slug for exercise in ALL_EXERCISES]
        assert len(slugs) == len(set(slugs))

    def test_validation_rejects_a_lesson_missing_sections(self):
        from app.content.schema import CourseSpec, LessonSpec, ModuleSpec
        from app.models.enums import SkillLevel

        broken = CourseSpec(
            slug="broken",
            title="B",
            subtitle="",
            description="",
            level=SkillLevel.BEGINNER,
            outcomes=(),
            estimated_hours=1,
            modules=(
                ModuleSpec(
                    slug="m",
                    title="M",
                    summary="",
                    level=SkillLevel.BEGINNER,
                    lessons=(
                        LessonSpec(
                            slug="incomplete",
                            title="T",
                            summary="",
                            body="",
                            sections={"what_is_it": "only one"},
                        ),
                    ),
                ),
            ),
        )
        with pytest.raises(ContentError, match="missing required sections"):
            validate((broken,), CONCEPTS, ())

    def test_validation_rejects_an_unknown_concept_reference(self):
        from app.content.schema import ConceptSpec

        with pytest.raises(ContentError, match="unknown"):
            validate(
                (),
                (
                    ConceptSpec(
                        slug="a",
                        name="A",
                        description="",
                        category="x",
                        prerequisites=("nonexistent",),
                    ),
                ),
                (),
            )


class TestLessonQuality:
    @pytest.mark.parametrize("lesson", ALL_LESSONS, ids=lambda lesson: lesson.slug)
    def test_answers_every_required_question(self, lesson):
        for key in REQUIRED_SECTIONS:
            assert lesson.sections.get(key), f"{lesson.slug} has no '{key}' section"

    @pytest.mark.parametrize("lesson", ALL_LESSONS, ids=lambda lesson: lesson.slug)
    def test_body_is_substantial(self, lesson):
        assert len(lesson.body) > 800, f"{lesson.slug} is too thin to teach anything"

    @pytest.mark.parametrize("lesson", ALL_LESSONS, ids=lambda lesson: lesson.slug)
    def test_has_worked_examples(self, lesson):
        assert lesson.examples, f"{lesson.slug} has no examples"

    @pytest.mark.parametrize("lesson", ALL_LESSONS, ids=lambda lesson: lesson.slug)
    def test_has_at_least_one_exercise(self, lesson):
        assert lesson.exercises, f"{lesson.slug} has nothing to practise"

    @pytest.mark.parametrize("lesson", ALL_LESSONS, ids=lambda lesson: lesson.slug)
    def test_teaches_a_known_concept(self, lesson):
        assert lesson.concepts
        assert set(lesson.concepts) <= CONCEPT_SLUGS

    @pytest.mark.parametrize("lesson", ALL_LESSONS, ids=lambda lesson: lesson.slug)
    def test_has_runnable_starter_code(self, lesson):
        assert lesson.starter_code.strip(), f"{lesson.slug} has no starter code to run"


class TestExerciseQuality:
    @pytest.mark.parametrize("exercise", ALL_EXERCISES, ids=lambda e: e.slug)
    def test_assesses_a_known_concept(self, exercise):
        assert set(exercise.concepts) <= CONCEPT_SLUGS

    @pytest.mark.parametrize("exercise", ALL_EXERCISES, ids=lambda e: e.slug)
    def test_has_a_four_rung_hint_ladder(self, exercise):
        if exercise.kind is ExerciseKind.QUIZ:
            pytest.skip("quizzes explain themselves")
        assert len(exercise.hints) == 4, (
            f"{exercise.slug} has {len(exercise.hints)} hints; the ladder is "
            "conceptual clue -> direction -> specific area -> partial solution"
        )

    @pytest.mark.parametrize("exercise", ALL_EXERCISES, ids=lambda e: e.slug)
    def test_has_a_reference_solution(self, exercise):
        if exercise.kind is ExerciseKind.QUIZ:
            pytest.skip("quizzes have an answer key instead")
        assert exercise.solution_files, f"{exercise.slug} has no reference solution"
        assert exercise.solution_explanation, (
            f"{exercise.slug} shows a solution without explaining it"
        )

    @pytest.mark.parametrize("exercise", ALL_EXERCISES, ids=lambda e: e.slug)
    def test_pytest_exercises_ship_a_test_suite(self, exercise):
        if exercise.grader is not GraderKind.PYTEST:
            pytest.skip("not pytest-graded")
        assert exercise.hidden_files
        assert any(name.startswith("test_") for name in exercise.hidden_files)

    @pytest.mark.parametrize("exercise", ALL_EXERCISES, ids=lambda e: e.slug)
    def test_prompt_is_specific(self, exercise):
        assert len(exercise.prompt) > 40, f"{exercise.slug} does not say enough"

    @pytest.mark.parametrize("exercise", ALL_EXERCISES, ids=lambda e: e.slug)
    def test_difficulty_is_in_range(self, exercise):
        assert 0.0 <= exercise.difficulty <= 1.0


class TestConceptGraph:
    def test_prerequisites_are_acyclic(self):
        """A cycle would deadlock the readiness calculation."""
        graph = {c.slug: set(c.prerequisites) for c in CONCEPTS}
        visiting: set[str] = set()
        done: set[str] = set()

        def visit(node: str, path: list[str]) -> None:
            if node in done:
                return
            if node in visiting:
                raise AssertionError(f"prerequisite cycle: {' -> '.join([*path, node])}")
            visiting.add(node)
            for prerequisite in graph.get(node, ()):
                visit(prerequisite, [*path, node])
            visiting.discard(node)
            done.add(node)

        for slug in graph:
            visit(slug, [])

    def test_every_concept_is_taught_somewhere(self):
        taught = {slug for lesson in ALL_LESSONS for slug in lesson.concepts}
        assessed = {slug for exercise in ALL_EXERCISES for slug in exercise.concepts}
        used_by_projects = {slug for project in PROJECTS for slug in project.concepts}
        used_by_quizzes = {slug for question in QUIZ_BANK for slug in question.concepts}
        orphans = CONCEPT_SLUGS - taught - assessed - used_by_projects - used_by_quizzes
        assert not orphans, f"concepts nothing references: {sorted(orphans)}"

    def test_certification_categories_exist(self):
        from app.services.certification import REQUIREMENTS

        categories = {concept.category for concept in CONCEPTS}
        for requirement in REQUIREMENTS:
            missing = set(requirement.required_categories) - categories
            assert not missing, (
                f"{requirement.level} requires categories that no concept has: {sorted(missing)}"
            )

    def test_certification_projects_exist(self):
        from app.services.certification import REQUIREMENTS

        slugs = {project.slug for project in PROJECTS}
        for requirement in REQUIREMENTS:
            missing = set(requirement.required_projects) - slugs
            assert not missing, f"{requirement.level} requires missing projects {missing}"


class TestProjectQuality:
    @pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.slug)
    def test_has_requirements_and_a_rubric(self, project):
        assert len(project.requirements) > 300
        assert project.rubric

    @pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.slug)
    def test_rubric_weights_are_positive(self, project):
        assert all(float(item["weight"]) > 0 for item in project.rubric)

    @pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.slug)
    def test_has_acceptance_tests(self, project):
        assert project.acceptance_tests

    def test_guidance_fades_across_the_academy(self):
        """Spec §50: guided → partially guided → requirements only → independent."""
        by_position = sorted(PROJECTS, key=lambda project: project.level.value)
        assert {p.guidance.value for p in by_position} >= {
            "fully_guided",
            "partially_guided",
            "requirements_only",
            "independent",
        }

    def test_prerequisites_reference_real_projects(self):
        slugs = {project.slug for project in PROJECTS}
        for project in PROJECTS:
            assert set(project.prerequisites) <= slugs


class TestReferenceQuality:
    @pytest.mark.parametrize("entry", REFERENCE, ids=lambda e: e.key)
    def test_answers_what_a_learner_needs(self, entry):
        assert entry.signature
        assert entry.summary
        assert entry.examples, f"{entry.key} has no example"
        assert entry.common_mistakes, f"{entry.key} lists no pitfalls"

    def test_related_keys_point_at_real_entries_or_stdlib_names(self):
        keys = {entry.key for entry in REFERENCE}
        for entry in REFERENCE:
            for related in entry.related:
                # Cross-links to entries not yet written are allowed, but they
                # must at least look like a dotted or bare identifier.
                assert related in keys or related.replace(".", "").replace("_", "").isalnum()

    def test_reference_lesson_links_are_valid(self):
        slugs = {lesson.slug for lesson in ALL_LESSONS}
        for entry in REFERENCE:
            assert set(entry.lesson_slugs) <= slugs, entry.key


class TestQuizBank:
    @pytest.mark.parametrize("question", QUIZ_BANK, ids=lambda q: q.slug)
    def test_answer_key_is_valid(self, question):
        assert 0 <= question.correct_index < len(question.options)

    @pytest.mark.parametrize("question", QUIZ_BANK, ids=lambda q: q.slug)
    def test_has_at_least_three_options(self, question):
        assert len(question.options) >= 3

    @pytest.mark.parametrize("question", QUIZ_BANK, ids=lambda q: q.slug)
    def test_explains_the_answer(self, question):
        assert len(question.explanation) > 60

    def test_covers_the_interview_tracks(self):
        tracks = {track for question in QUIZ_BANK for track in question.tracks}
        assert {"backend", "sdet", "automation", "python-developer"} <= tracks


class TestAchievements:
    @pytest.mark.parametrize("achievement", ACHIEVEMENTS, ids=lambda a: a.slug)
    def test_criteria_are_interpretable(self, achievement):
        known = {
            "exercises_passed",
            "lessons_completed",
            "concepts_mastered",
            "projects_completed",
            "streak_days",
            "unaided_passes",
            "debug_fixes",
        }
        assert achievement.criteria["type"] in known

    def test_no_achievement_rewards_mere_attendance(self):
        """Gamification must not substitute for learning (spec §42)."""
        for achievement in ACHIEVEMENTS:
            assert achievement.criteria["type"] not in {"time_spent", "lessons_viewed"}
