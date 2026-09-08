"""The ported mastery engine must agree with the Python one.

``frontend/src/static/mastery.ts`` is a hand port of
``app/services/mastery.py``, needed because the Python module is bound to
SQLAlchemy and the static build has no database. A port is a fork, and a fork
drifts — so this compares them numerically instead of trusting the comments.

Node runs the TypeScript directly via its built-in type stripping, so this needs
no bundler and no test framework on the JavaScript side.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from app.services.mastery import (
    CONFIDENCE_GAIN,
    Evidence,
    band_for,
    retention_factor,
    target_for,
)

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "frontend" / "src" / "static" / "mastery.ts"

#: Floating-point arithmetic differs in the last bits between the two runtimes;
#: anything above this would be a real difference in the formula.
TOLERANCE = 1e-9

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not MODULE.exists(),
    reason="node or the ported mastery module is unavailable",
)


def run_ts(expression_body: str) -> Any:
    """Evaluate a snippet against the ported module and return its JSON result."""
    script = f"""
import {{
  evidenceValue, targetFor, bandFor, confidenceFor, retentionFactor, record, xpFor, view,
}} from {str(MODULE)!r};
{expression_body}
"""
    result = subprocess.run(  # noqa: S603
        ["node", "--input-type=module", "-e", script],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"node failed:\n{result.stderr[-2000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


#: Observations spanning every branch of the evidence calculation.
EVIDENCE_CASES: list[dict[str, Any]] = [
    {"raw_score": 1.0},
    {"raw_score": 0.0},
    {"raw_score": 0.5},
    {"raw_score": 1.0, "hints_used": 1},
    {"raw_score": 1.0, "hints_used": 3},
    # Past the point where the hint discount floors out at 0.35.
    {"raw_score": 1.0, "hints_used": 10},
    {"raw_score": 1.0, "solution_viewed": True},
    {"raw_score": 1.0, "hints_used": 2, "solution_viewed": True},
    # Fast: pace bonus.
    {"raw_score": 1.0, "time_spent_seconds": 30, "expected_seconds": 120},
    # Slow: pace discount.
    {"raw_score": 1.0, "time_spent_seconds": 600, "expected_seconds": 120},
    # In between: no pace effect.
    {"raw_score": 1.0, "time_spent_seconds": 120, "expected_seconds": 120},
    # A zero score must not attract a pace bonus.
    {"raw_score": 0.0, "time_spent_seconds": 10, "expected_seconds": 120},
    # Out-of-range input must clamp identically on both sides.
    {"raw_score": 1.5},
    {"raw_score": -0.5},
]


class TestEvidenceValue:
    """`e = raw × hint_discount × solution_discount × pace`."""

    def test_every_branch_agrees(self) -> None:
        expected = [Evidence(**case).value() for case in EVIDENCE_CASES]
        cases_js = json.dumps(
            [
                {
                    "rawScore": case["raw_score"],
                    "hintsUsed": case.get("hints_used", 0),
                    "solutionViewed": case.get("solution_viewed", False),
                    "timeSpentSeconds": case.get("time_spent_seconds", 0),
                    "expectedSeconds": case.get("expected_seconds", 0),
                }
                for case in EVIDENCE_CASES
            ]
        )
        actual = run_ts(f"console.log(JSON.stringify({cases_js}.map(evidenceValue)));")

        assert len(actual) == len(expected)
        for case, want, got in zip(EVIDENCE_CASES, expected, actual, strict=True):
            assert abs(want - got) < TOLERANCE, f"{case}: python={want} ts={got}"


class TestTargetFor:
    """Difficulty weighting, on both the success and failure side of 0.5."""

    def test_it_agrees_across_the_grid(self) -> None:
        values = [0.0, 0.2, 0.49, 0.5, 0.51, 0.8, 1.0]
        difficulties = [0.0, 0.25, 0.5, 0.75, 1.0]
        expected = [target_for(v, d) for v in values for d in difficulties]
        actual = run_ts(
            f"const vs={json.dumps(values)}, ds={json.dumps(difficulties)};"
            "const out=[]; for (const v of vs) for (const d of ds) out.push(targetFor(v,d));"
            "console.log(JSON.stringify(out));"
        )
        for want, got in zip(expected, actual, strict=True):
            assert abs(want - got) < TOLERANCE


class TestBandFor:
    """Band boundaries — these drive user-visible labels and colours."""

    def test_boundaries_agree(self) -> None:
        scores = [0.0, 0.24, 0.25, 0.49, 0.5, 0.69, 0.7, 0.84, 0.85, 0.99, 1.0]
        expected = [band_for(score, 1).value for score in scores]
        actual = run_ts(
            f"console.log(JSON.stringify({json.dumps(scores)}.map((s) => bandFor(s, 1))));"
        )
        assert actual == expected

    def test_no_attempts_is_not_started_on_both_sides(self) -> None:
        assert band_for(0.9, 0).value == "not_started"
        assert run_ts("console.log(JSON.stringify(bandFor(0.9, 0)));") == "not_started"


class TestConfidence:
    """The port uses a closed form where Python uses a recurrence."""

    def test_the_closed_form_matches_the_recurrence(self) -> None:
        """`c' = c + (1-c)·g` iterated n times equals `1 - (1-g)^n`."""
        expected = []
        confidence = 0.0
        for _ in range(25):
            confidence = confidence + (1.0 - confidence) * CONFIDENCE_GAIN
            expected.append(confidence)

        actual = run_ts(
            "const out=[]; for (let n = 1; n <= 25; n++) out.push(confidenceFor(n));"
            "console.log(JSON.stringify(out));"
        )
        for index, (want, got) in enumerate(zip(expected, actual, strict=True), start=1):
            assert abs(want - got) < TOLERANCE, f"after {index} attempts: {want} vs {got}"

    def test_zero_attempts_is_zero_confidence(self) -> None:
        assert run_ts("console.log(JSON.stringify(confidenceFor(0)));") == 0


class TestRetentionFactor:
    """Forgetting curve, including the floor."""

    @pytest.mark.parametrize("days", [0, 1, 7, 12, 30, 90, 365, 3650])
    @pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
    def test_it_agrees(self, days: int, confidence: float) -> None:
        from datetime import UTC, datetime, timedelta

        when = datetime.now(UTC) - timedelta(days=days)
        expected = retention_factor(when, confidence)
        actual = run_ts(
            f"console.log(JSON.stringify(retentionFactor({when.isoformat()!r}, {confidence})));"
        )
        # Seconds elapse between the two computations, so allow a wider margin
        # here than elsewhere; the floor and the shape are what matter.
        assert abs(expected - actual) < 1e-4

    def test_never_practised_does_not_decay(self) -> None:
        assert retention_factor(None, 0.5) == 1.0
        assert run_ts("console.log(JSON.stringify(retentionFactor(null, 0.5)));") == 1.0

    def test_it_is_floored(self) -> None:
        """A long absence must not zero a score; that would erase real learning."""
        assert run_ts(
            "console.log(JSON.stringify(retentionFactor('2000-01-01T00:00:00Z', 0)));"
        ) == (pytest.approx(0.55))


class TestRecordedScoreSequence:
    """A replayed history must land on the same score in both engines."""

    @pytest.mark.parametrize(
        "sequence",
        [
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
            [0.5, 1.0, 0.0, 1.0, 0.75],
            [1.0] * 12,
            [0.2, 0.4, 0.6, 0.8, 1.0],
        ],
    )
    def test_folding_evidence_agrees(self, sequence: list[float]) -> None:
        """Reimplements the Python blend directly, since the service needs a DB."""
        from app.services.mastery import BASE_LEARNING_RATE

        score = 0.0
        confidence = 0.0
        for raw in sequence:
            value = Evidence(raw_score=raw, difficulty=0.5).value()
            target = target_for(value, 0.5)
            alpha = BASE_LEARNING_RATE * (1.0 - 0.6 * confidence)
            score = max(0.0, min(1.0, score + alpha * (target - score)))
            confidence = confidence + (1.0 - confidence) * CONFIDENCE_GAIN

        actual = run_ts(
            f"let c = undefined; for (const raw of {json.dumps(sequence)}) "
            "c = record(c, { rawScore: raw, difficulty: 0.5 });"
            "console.log(JSON.stringify(c.score));"
        )
        assert abs(score - actual) < TOLERANCE


class TestXpAward:
    """XP discounts, mirroring SubmissionService._award_xp."""

    @pytest.mark.parametrize(
        ("first", "hints", "solution"),
        [
            (True, 0, False),
            (False, 0, False),
            (True, 1, False),
            (True, 4, False),
            (True, 9, False),
            (True, 0, True),
            (False, 3, True),
        ],
    )
    def test_it_agrees(self, first: bool, hints: int, solution: bool) -> None:
        reward = 100
        xp = float(reward)
        if solution:
            xp *= 0.3
        elif hints:
            xp *= max(0.4, 1.0 - 0.15 * hints)
        if first and not hints and not solution:
            xp *= 1.25
        expected = int(round(xp))

        actual = run_ts(
            f"console.log(JSON.stringify(xpFor({reward}, {{ firstAttempt: {str(first).lower()},"
            f" hintsUsed: {hints}, solutionViewed: {str(solution).lower()} }})));"
        )
        assert actual == expected
