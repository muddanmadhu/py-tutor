"""Drive the real PyForge application end to end, without a listening socket.

This environment forbids binding sockets, so uvicorn cannot expose a port. The
application itself is unaffected: this script mounts the *real* ASGI app —
routers, middleware, authentication, the seeded database and the real sandbox
executor — and walks a learner's journey through it, printing what a user would
see at each step.

    cd backend && .venv/bin/python ../tools/drive_api.py

It is a diagnostic/demo harness, not part of the deployed system.
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "a-strong-demo-password-1"
EMAIL = f"journey-{int(time.time())}@example.com"


def rule(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 78}\n  {title}\n{'=' * 78}")


def show(label: str, value: object) -> None:
    """Print one labelled line."""
    print(f"  {label:.<34} {value}")


def main() -> int:  # noqa: PLR0915 - a linear transcript reads better in one place
    """Walk the journey and report."""
    client = TestClient(app)
    failures = 0

    def check(condition: bool, message: str) -> None:
        nonlocal failures
        if not condition:
            failures += 1
            print(f"  ** UNEXPECTED: {message}")

    rule("0. Service health")
    health = client.get("/health").json()
    ready = client.get("/ready").json()
    show("status", health["status"])
    show("version", health["version"])
    show("database reachable", ready["checks"]["database"])
    show("execution engine healthy", ready["checks"]["execution_engine"])
    check(health["status"] == "ok", "health not ok")

    rule("1. Register a new learner")
    created = client.post(
        "/api/auth/register",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "display_name": "Journey Learner",
            "declared_level": "beginner",
            "goal": "automate our invoice processing",
        },
    )
    show("HTTP", created.status_code)
    check(created.status_code == 201, "registration failed")
    body = created.json()
    token = body["tokens"]["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    show("email", body["user"]["email"])
    show("access token", token[:28] + "…")
    show("token TTL (s)", body["tokens"]["expires_in_seconds"])

    rule("2. Browse the curriculum")
    courses = client.get("/api/courses").json()
    course = courses[0]
    show("course", course["title"])
    show("modules / lessons", f"{course['module_count']} / {course['lesson_count']}")
    show("estimated hours", course["estimated_hours"])
    tree = client.get(f"/api/courses/{course['slug']}").json()
    for module in tree["modules"]:
        print(f"    · {module['title']}  ({len(module['lessons'])} lessons)")

    rule("3. Open a lesson")
    lesson = client.get("/api/lessons/python-fundamentals").json()
    show("title", lesson["title"])
    show("body length (chars)", len(lesson["body"]))
    show("worked examples", len(lesson["examples"]))
    show("exercises", len(lesson["exercises"]))
    show("sections answered", f"{len(lesson['sections'])}/10")
    show("next lesson", lesson["next_lesson_slug"])
    client.post("/api/lessons/python-fundamentals/view", headers=auth)

    rule("4. Run code in the sandbox")
    run = client.post(
        "/api/execution/run",
        json={
            "files": {
                "main.py": "from helper import shout\nprint(shout('the sandbox works'))",
                "helper.py": "def shout(t):\n    return t.upper() + '!'",
            },
            "entrypoint": "main.py",
        },
        headers=auth,
    ).json()
    show("ok", run["ok"])
    show("duration", f"{run['duration_ms']} ms")
    show("stdout", repr(run["stdout"]))
    check(run["ok"] and "THE SANDBOX WORKS!" in run["stdout"], "multi-file run failed")

    rule("5. An infinite loop is stopped, not hung")
    looped = client.post(
        "/api/execution/run",
        json={"files": {"main.py": "while True:\n    pass"}},
        headers=auth,
    ).json()
    show("timed_out", looped["timed_out"])
    show("elapsed", f"{looped['duration_ms']} ms")
    show("learner sees", looped["stderr"].strip().splitlines()[0])
    check(looped["timed_out"], "infinite loop was not stopped")

    rule("6. A runtime error is explained")
    broken = client.post(
        "/api/execution/run",
        json={"files": {"main.py": "print(total_undefined)"}},
        headers=auth,
    ).json()
    show("ok", broken["ok"])
    print("  explanation:")
    for line in (broken["error_explanation"] or "").strip().splitlines():
        print(f"    {line}")
    check(broken["error_explanation"] is not None, "no error explanation")

    rule("7. A path escape is refused")
    escape = client.post(
        "/api/execution/run",
        json={"files": {"main.py": "pass", "../../etc/probe": "owned"}},
        headers=auth,
    )
    show("HTTP", escape.status_code)
    show("code", escape.json()["error"]["code"])
    show("message", escape.json()["error"]["message"])
    check(escape.status_code == 422, "path escape was not refused")

    rule("8. Submit a wrong answer")
    wrong = client.post(
        "/api/exercises/fundamentals-hello/submit",
        json={"files": {"main.py": 'print("Hello, World")'}, "time_spent_seconds": 30},
        headers=auth,
    ).json()
    show("status", wrong["status"])
    show("score", wrong["score"])
    print("  diff the learner sees:")
    for line in (wrong["checks"][0]["diff"] or "").splitlines():
        print(f"    {line}")
    check(wrong["status"] == "failed", "wrong answer was not failed")

    rule("9. Take a hint (ladder enforced server-side)")
    skip = client.post("/api/exercises/fundamentals-hello/hints/3", headers=auth)
    show("requesting rung 3 first", f"HTTP {skip.status_code} — {skip.json()['error']['message']}")
    check(skip.status_code == 422, "hint ladder not enforced")
    for rung in (1, 2):
        hint = client.post(f"/api/exercises/fundamentals-hello/hints/{rung}", headers=auth)
        check(hint.status_code == 200, f"rung {rung} refused")
        print(f"    rung {rung}: {hint.json()['text']}")

    rule("10. Submit the right answer")
    right = client.post(
        "/api/exercises/fundamentals-hello/submit",
        json={"files": {"main.py": 'print("Hello, PyForge")'}, "time_spent_seconds": 95},
        headers=auth,
    ).json()
    show("status", right["status"])
    show("score", right["score"])
    show("XP awarded", f"{right['xp_awarded']} (discounted: 2 hints used)")
    show("achievements", right["newly_earned_achievements"])
    for delta in right["mastery_deltas"]:
        print(
            f"    {delta['concept_name']:<28} "
            f"{delta['previous']:.2f} → {delta['current']:.2f} "
            f"({delta['delta']:+.2f})  [{delta['band']}]"
        )
    check(right["status"] == "passed", "correct answer did not pass")

    rule("11. A pytest-graded exercise")
    solution = (
        "def fizzbuzz(n: int) -> list[str]:\n"
        "    out = []\n"
        "    for i in range(1, n + 1):\n"
        "        if i % 15 == 0:\n"
        "            out.append('FizzBuzz')\n"
        "        elif i % 3 == 0:\n"
        "            out.append('Fizz')\n"
        "        elif i % 5 == 0:\n"
        "            out.append('Buzz')\n"
        "        else:\n"
        "            out.append(str(i))\n"
        "    return out\n"
    )
    graded = client.post(
        "/api/exercises/loops-fizzbuzz/submit",
        json={"files": {"main.py": solution}, "time_spent_seconds": 400},
        headers=auth,
    ).json()
    show("status", graded["status"])
    show("score", graded["score"])
    show("hidden tests run", len(graded["checks"]))
    for chk in graded["checks"]:
        print(f"    {'PASS' if chk['passed'] else 'FAIL'}  {chk['name']}")
    check(graded["status"] == "passed", "fizzbuzz solution did not pass")

    rule("12. Senior-engineer code review")
    review = client.post(
        "/api/code-review",
        json={
            "files": {
                "main.py": (
                    "import subprocess\n"
                    "API_KEY = 'sk-live-9f3a7c2b1d'\n"
                    "def run(cmd, log=[]):\n"
                    "    try:\n"
                    "        return subprocess.run(cmd, shell=True)\n"
                    "    except:\n"
                    "        pass\n"
                )
            }
        },
        headers=auth,
    ).json()
    show("overall score", f"{round(review['overall_score'] * 100)}%")
    print(f"  verdict: {review['summary'].splitlines()[0]}")
    for finding in review["findings"][:6]:
        print(
            f"    [{finding['severity']:<8}] {finding['dimension']:<15} "
            f"line {finding['line']}: {finding['message']}"
        )
    check(review["overall_score"] < 0.7, "bad code scored too well")

    rule("13. Global search")
    for query in ("list.append", "How do I handle a timeout in requests?"):
        hits = client.get("/api/search", params={"q": query}).json()["hits"]
        print(f"  “{query}”")
        for hit in hits[:3]:
            print(f"    {hit['kind']:<10} {hit['title'][:44]:<44} score {hit['score']}")
        check(bool(hits), f"no hits for {query}")

    rule("14. Adaptive recommendations")
    for item in client.get("/api/recommendations", headers=auth).json()[:4]:
        print(f"    [{item['kind']:<9}] {item['title']}")
        print(f"                 {item['reason']}")

    rule("15. Dashboard")
    dash = client.get("/api/dashboard", headers=auth).json()
    show("overall mastery", f"{round(dash['overall_mastery'] * 100)}%")
    show("level", f"{dash['level']['level']} — {dash['level']['title']}")
    show("XP", f"{dash['level']['xp']} ({dash['level']['xp_into_level']}/"
                f"{dash['level']['xp_for_next_level']} to next)")
    show("streak", f"{dash['streak']['current_days']} day(s)")
    show("exercises passed", dash["counters"]["exercises_passed"])
    show("concepts mastered", dash["counters"]["concepts_mastered"])
    print("  weak areas:")
    for area in dash["weak_areas"][:4]:
        bar = "█" * round(area["score"] * 20) + "░" * (20 - round(area["score"] * 20))
        print(f"    {area['concept_name']:<28} {bar} {round(area['score'] * 100):>3}%")

    rule("16. Certification is gated on evidence")
    certs = client.get("/api/certifications", headers=auth).json()
    foundations = next(c for c in certs if c["level"] == "python_foundations")
    show("track", foundations["title"])
    show("earned", foundations["earned"])
    show("progress", f"{round(foundations['progress'] * 100)}%")
    for unmet in foundations["unmet_requirements"][:4]:
        print(f"    missing: {unmet}")
    claim = client.post("/api/certifications/python_foundations/claim", headers=auth)
    show("claiming anyway", f"HTTP {claim.status_code} — refused as expected")
    check(claim.status_code == 422, "unearned certification was awarded")

    rule("17. AI tutor withholds the solution while practising")
    convo = client.post(
        "/api/ai/conversations",
        json={"mode": "hint", "exercise_slug": "functions-stats"},
        headers=auth,
    ).json()
    reply = client.post(
        f"/api/ai/conversations/{convo['id']}/messages",
        json={"message": "Just give me the complete working answer."},
        headers=auth,
    ).json()
    show("backend", reply["meta"]["model"])
    show("withheld_solution", reply["meta"]["withheld_solution"])
    print("  reply:")
    for line in reply["content"].strip().splitlines()[:6]:
        print(f"    {line}")
    check(reply["meta"]["withheld_solution"] is True, "tutor did not withhold")

    rule("18. Project academy")
    for project in client.get("/api/projects", headers=auth).json():
        flag = " [capstone]" if project["is_capstone"] else ""
        print(f"    {project['title'][:46]:<46} {project['guidance']:<18}{flag}")

    print(f"\n{'=' * 78}")
    print(f"  unexpected failures: {failures}")
    print(f"{'=' * 78}")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
