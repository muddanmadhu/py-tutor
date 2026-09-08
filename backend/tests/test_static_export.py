"""The exported content must carry the fields the client reads.

TypeScript checks that `endpoints.static.ts` matches its HTTP twin, but nothing
checks the *data*: a field can exist on a TypeScript interface and simply be
absent from the JSON the exporter produced. That reads as `undefined` at runtime
and shows up as an empty panel on the published site rather than as a build
failure, which is the worst place to find it.

So this asserts the contract from the data side, for the documents the static
build actually depends on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
EXPORTER = REPO / "tools" / "export_static.py"


@pytest.fixture(scope="module")
def content(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run the exporter and return the content root."""
    out = tmp_path_factory.mktemp("content")
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(EXPORTER), "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"the exporter failed:\n{result.stderr[-2000:]}")
    return out


def read(root: Path, relative: str) -> Any:
    """Load one exported document."""
    path = root / relative
    assert path.exists(), f"the exporter did not write {relative}"
    return json.loads(path.read_text(encoding="utf-8"))


def assert_fields(document: Any, fields: list[str], label: str) -> None:
    """Every named field must be present, though it may legitimately be null."""
    missing = [field for field in fields if field not in document]
    assert not missing, f"{label} is missing {missing}"


class TestTheTreeIsComplete:
    """Every file the client fetches by a fixed path must exist."""

    @pytest.mark.parametrize(
        "relative",
        [
            "courses.json",
            "exercises.json",
            "challenges.json",
            "concepts.json",
            "reference.json",
            "projects.json",
            "interview.json",
            "search-index.json",
            "manifest.json",
            "grader.py",
            "reviewer.py",
        ],
    )
    def test_it_exists(self, content: Path, relative: str) -> None:
        assert (content / relative).exists(), f"{relative} was not exported"

    def test_every_course_lesson_was_exported(self, content: Path) -> None:
        """A lesson listed in a course but not exported is a dead link."""
        for summary in read(content, "courses.json"):
            course = read(content, f"courses/{summary['slug']}.json")
            for module in course["modules"]:
                for lesson in module["lessons"]:
                    assert (content / "lessons" / f"{lesson['slug']}.json").exists(), (
                        f"lesson {lesson['slug']} is listed in {summary['slug']} but not exported"
                    )

    def test_every_lesson_exercise_was_exported(self, content: Path) -> None:
        for path in (content / "lessons").glob("*.json"):
            lesson = json.loads(path.read_text(encoding="utf-8"))
            for exercise in lesson.get("exercises", []):
                assert (content / "exercises" / f"{exercise['slug']}.json").exists(), (
                    f"exercise {exercise['slug']} is listed in {path.stem} but not exported"
                )

    def test_every_reference_entry_was_exported(self, content: Path) -> None:
        for entry in read(content, "reference.json"):
            assert (content / "reference" / f"{entry['key']}.json").exists()

    def test_every_project_was_exported(self, content: Path) -> None:
        for summary in read(content, "projects.json"):
            assert (content / "projects" / f"{summary['slug']}.json").exists()


class TestFieldsTheClientReads:
    """Named against the code that reads them, so a failure points somewhere."""

    def test_course_summary(self, content: Path) -> None:
        """`progress.dashboard` sums `lesson_count` for the lessons total."""
        courses = read(content, "courses.json")
        assert courses, "no courses were exported"
        assert_fields(courses[0], ["slug", "title", "lesson_count"], "course summary")

    def test_lesson_detail(self, content: Path) -> None:
        """`curriculum.lesson` overlays local state onto these."""
        path = next((content / "lessons").glob("*.json"))
        assert_fields(
            json.loads(path.read_text(encoding="utf-8")),
            ["slug", "title", "progress", "exercises"],
            "lesson detail",
        )

    def test_exercise_summary(self, content: Path) -> None:
        """`withSummaryState` rewrites `best_score` and `status` on these."""
        assert_fields(
            read(content, "exercises.json")[0],
            ["slug", "title", "kind", "level", "best_score", "status"],
            "exercise summary",
        )

    def test_every_exercise_can_be_graded(self, content: Path) -> None:
        """The gated extras and the mastery inputs, on *every* exercise.

        Checked exhaustively rather than on a sample: one exercise missing
        `grader_config` is one exercise nobody can pass.
        """
        paths = sorted((content / "exercises").glob("*.json"))
        assert paths, "no exercises were exported"
        for path in paths:
            document = json.loads(path.read_text(encoding="utf-8"))
            assert_fields(
                document,
                [
                    # Gated content the browser cannot request.
                    "hints",
                    "solution",
                    "grader_config",
                    "misconception_rules",
                    # Read by `exercises.submit` to move mastery and award XP.
                    "concept_slugs",
                    "difficulty",
                    "estimated_minutes",
                    "xp_reward",
                    # Decides whether the code has to run before grading.
                    "execution_plan",
                ],
                f"exercise {path.stem}",
            )

    def test_exercises_needing_execution_have_a_plan(self, content: Path) -> None:
        """stdout_match and pytest cannot be graded without running the code."""
        for path in sorted((content / "exercises").glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["grader"] in {"stdout_match", "pytest"}:
                plan = document["execution_plan"]
                assert plan is not None, f"{path.stem} needs an execution plan and has none"
                assert_fields(
                    plan, ["mode", "entrypoint", "stdin", "extra_files"], f"plan for {path.stem}"
                )
            else:
                # Graded from source alone; a plan would mean a pointless run.
                assert document["execution_plan"] is None, (
                    f"{path.stem} is graded from source but carries an execution plan"
                )

    def test_pytest_exercises_ship_their_tests(self, content: Path) -> None:
        """Without the hidden suite there is nothing for pytest to run."""
        for path in sorted((content / "exercises").glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["grader"] == "pytest":
                extras = document["execution_plan"]["extra_files"]
                assert extras, f"{path.stem} is pytest-graded but ships no test files"
                assert any(
                    name.startswith("test_") or name.endswith("_test.py") for name in extras
                ), f"{path.stem} ships {list(extras)}, none of which pytest will collect"

    def test_multiple_choice_exercises_ship_their_options(self, content: Path) -> None:
        for path in sorted((content / "exercises").glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["grader"] == "multiple_choice":
                config = document["grader_config"]
                assert_fields(config, ["options", "correct_index"], f"{path.stem} grader_config")
                assert config["options"], f"{path.stem} has no options to choose from"

    def test_concepts(self, content: Path) -> None:
        """`masteryItems` names concepts from these instead of showing slugs."""
        assert_fields(
            read(content, "concepts.json")[0],
            ["slug", "name", "category", "level"],
            "concept",
        )

    def test_every_exercise_concept_is_in_the_index(self, content: Path) -> None:
        """Otherwise mastery shows a raw slug where a name should be."""
        known = {concept["slug"] for concept in read(content, "concepts.json")}
        for path in sorted((content / "exercises").glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            unknown = set(document["concept_slugs"]) - known
            assert not unknown, f"{path.stem} references unknown concepts {sorted(unknown)}"

    def test_reference(self, content: Path) -> None:
        assert_fields(
            read(content, "reference.json")[0],
            ["key", "title", "kind", "module", "summary"],
            "reference summary",
        )

    def test_interview_questions_carry_their_answers(self, content: Path) -> None:
        """There is no server left to POST an answer to for marking."""
        questions = read(content, "interview.json")
        assert questions, "no interview questions were exported"
        for question in questions:
            assert_fields(
                question,
                ["slug", "question", "options", "tracks", "level", "correct_index", "explanation"],
                f"question {question.get('slug')}",
            )
            assert 0 <= question["correct_index"] < len(question["options"]), (
                f"question {question['slug']} has correct_index out of range"
            )

    def test_search_index(self, content: Path) -> None:
        entries = read(content, "search-index.json")
        assert entries, "the search index is empty"
        for entry in entries:
            assert_fields(entry, ["kind", "slug", "title", "snippet", "url"], "search entry")

    def test_project_detail(self, content: Path) -> None:
        """`projects.run` falls back to `starter_files` when nothing is saved."""
        summary = read(content, "projects.json")[0]
        assert_fields(
            read(content, f"projects/{summary['slug']}.json"),
            ["slug", "requirements", "workspace", "starter_files"],
            "project detail",
        )


class TestNoLeakedArtefacts:
    """The tree is served as-is, so nothing extra should be in it."""

    def test_no_bytecode_is_shipped(self, content: Path) -> None:
        """Importing the vendored modules locally can leave __pycache__ behind."""
        assert not list(content.rglob("__pycache__")), "bytecode leaked into the content tree"

    def test_the_vendored_modules_are_standalone(self, content: Path) -> None:
        for name in ("grader.py", "reviewer.py"):
            source = (content / name).read_text(encoding="utf-8")
            assert "from app." not in source, f"{name} still imports the application package"


class TestTheExportIsReproducible:
    """Two exports of the same curriculum must produce identical bytes.

    The tree is committed so that static-site build images need no Python, and
    CI guards against staleness by re-exporting and diffing. That check is only
    meaningful if the export is deterministic — otherwise it fails on every push
    and everyone learns to ignore it.

    Two things broke this when the check was first added: a timestamp recording
    when the export ran, and database queries returning concept lists in an
    arbitrary order.
    """

    def test_a_second_export_is_byte_identical(self, content: Path, tmp_path: Path) -> None:
        second = tmp_path / "again"
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(EXPORTER), "--out", str(second)],
            capture_output=True,
            text=True,
            cwd=REPO,
            check=False,
        )
        assert result.returncode == 0, result.stderr[-2000:]

        first_files = {p.relative_to(content) for p in content.rglob("*") if p.is_file()}
        second_files = {p.relative_to(second) for p in second.rglob("*") if p.is_file()}
        assert first_files == second_files, "the two exports contain different files"

        differing = [
            str(relative)
            for relative in sorted(first_files)
            if (content / relative).read_bytes() != (second / relative).read_bytes()
        ]
        assert not differing, (
            "the export is not reproducible, so the CI staleness check would fail on "
            f"every push. Differing files: {differing[:10]}"
        )

    def test_unordered_lists_are_sorted(self, content: Path) -> None:
        """Sorting is what makes arbitrary query order stop mattering.

        Only lists reached through one of the keys in ``UNORDERED_LIST_KEYS`` are
        sorted. ``concepts.json`` is a top-level list ordered by the API itself,
        so it is covered by the reproducibility test above rather than here.
        """
        for path in sorted((content / "exercises").glob("*.json")):
            slugs = json.loads(path.read_text(encoding="utf-8"))["concept_slugs"]
            assert slugs == sorted(slugs), f"{path.stem} has unsorted concept_slugs"

        for path in sorted((content / "lessons").glob("*.json")):
            lesson = json.loads(path.read_text(encoding="utf-8"))
            embedded = [concept["slug"] for concept in lesson.get("concepts", [])]
            assert embedded == sorted(embedded), f"{path.stem} has unsorted concepts"

    def test_ordered_lists_are_left_alone(self, content: Path) -> None:
        """Sorting these would change the content, not merely its bytes."""
        for path in sorted((content / "exercises").glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))

            # The hint ladder is positional: rung 1 must come before rung 2.
            levels = [hint["level"] for hint in document["hints"]]
            assert levels == sorted(levels), f"{path.stem} hint ladder is out of order"

            # Options are positional too — correct_index points into them — so a
            # sorted-looking list here would be a coincidence, not a guarantee.
            if document["grader"] == "multiple_choice":
                options = document["grader_config"]["options"]
                index = document["grader_config"]["correct_index"]
                assert 0 <= index < len(options), (
                    f"{path.stem} correct_index {index} does not address its options"
                )
