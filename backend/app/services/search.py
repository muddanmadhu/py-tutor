"""Global search across lessons, concepts, reference entries, exercises and projects.

Implementation notes
--------------------
The ranking is a small, explicit scoring function rather than a database
full-text index. That is a deliberate trade for this stage: it behaves
identically on SQLite and PostgreSQL, it is easy to tune while the curriculum
is being written, and at seed-content scale (thousands of rows, not millions)
it is fast enough. ``docs/ARCHITECTURE.md`` records the migration path to
PostgreSQL ``tsvector`` when the corpus outgrows it.

The scoring rewards, in order: exact key match, prefix match on the title or
key, whole-word match, keyword-list match, then body match — so searching
``list.append`` puts the reference entry above the lesson that mentions it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Concept, Exercise, Lesson, Project, ReferenceEntry

#: Words too common in a Python curriculum to be worth matching on.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "how",
        "do",
        "i",
        "to",
        "in",
        "of",
        "for",
        "is",
        "and",
        "with",
        "python",
        "use",
        "using",
        "what",
        "when",
        "my",
        "on",
        "can",
    }
)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One search result."""

    kind: str
    slug: str
    title: str
    snippet: str
    score: float
    url: str
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the API."""
        return {
            "kind": self.kind,
            "slug": self.slug,
            "title": self.title,
            "snippet": self.snippet,
            "score": round(self.score, 3),
            "url": self.url,
            "meta": self.meta,
        }


def tokenize(query: str) -> list[str]:
    """Split a natural-language query into meaningful terms.

    Dotted identifiers survive intact (``list.append`` stays one token) because
    they are the highest-signal thing a learner can type.
    """
    raw = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*|\d+", query.lower())
    terms = [term for term in raw if term not in _STOPWORDS and len(term) > 1]
    return terms or raw


def _score(terms: list[str], *, key: str, title: str, body: str, keywords: list[str]) -> float:
    """Score one candidate document against the query terms."""
    key_l, title_l, body_l = key.lower(), title.lower(), body.lower()
    keyword_set = {k.lower() for k in keywords}
    total = 0.0

    for term in terms:
        if term == key_l:
            total += 12.0
        elif key_l.endswith(f".{term}") or key_l.startswith(f"{term}."):
            total += 7.0
        elif term in key_l:
            total += 4.0

        if title_l == term:
            total += 8.0
        elif title_l.startswith(term):
            total += 3.5
        elif re.search(rf"\b{re.escape(term)}\b", title_l):
            total += 3.0
        elif term in title_l:
            total += 1.5

        if term in keyword_set:
            total += 2.5

        occurrences = len(re.findall(rf"\b{re.escape(term)}\b", body_l))
        total += min(2.0, occurrences * 0.4)

    # Reward documents that match more of the query, not just one term loudly.
    matched = sum(
        1
        for term in terms
        if term in key_l or term in title_l or term in body_l or term in keyword_set
    )
    if terms:
        total *= 0.6 + 0.4 * (matched / len(terms))
    return total


def _snippet(text: str, terms: list[str], length: int = 180) -> str:
    """Extract a window of ``text`` around the first matching term."""
    if not text:
        return ""
    lowered = text.lower()
    position = next((lowered.find(term) for term in terms if lowered.find(term) >= 0), -1)
    if position < 0:
        return text[:length].strip() + ("…" if len(text) > length else "")
    start = max(0, position - length // 3)
    end = min(len(text), start + length)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


class SearchService:
    """Cross-entity search."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self, query: str, *, kinds: list[str] | None = None, limit: int = 20
    ) -> list[SearchHit]:
        """Search everything (or the requested ``kinds``) and rank the results."""
        terms = tokenize(query)
        if not terms:
            return []
        wanted = set(kinds or ["reference", "lesson", "concept", "exercise", "project"])
        hits: list[SearchHit] = []

        if "reference" in wanted:
            hits.extend(self._search_reference(terms))
        if "lesson" in wanted:
            hits.extend(self._search_lessons(terms))
        if "concept" in wanted:
            hits.extend(self._search_concepts(terms))
        if "exercise" in wanted:
            hits.extend(self._search_exercises(terms))
        if "project" in wanted:
            hits.extend(self._search_projects(terms))

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return [hit for hit in hits if hit.score > 0.5][:limit]

    # -- per-entity ---------------------------------------------------------

    def _like_clauses(self, column: Any, terms: list[str]) -> Any:
        return or_(*[column.ilike(f"%{term}%") for term in terms])

    def _search_reference(self, terms: list[str]) -> list[SearchHit]:
        rows = self._session.scalars(
            select(ReferenceEntry).where(
                or_(
                    self._like_clauses(ReferenceEntry.key, terms),
                    self._like_clauses(ReferenceEntry.title, terms),
                    self._like_clauses(ReferenceEntry.summary, terms),
                    self._like_clauses(ReferenceEntry.description, terms),
                )
            )
        ).all()
        return [
            SearchHit(
                kind="reference",
                slug=entry.key,
                title=entry.title,
                snippet=_snippet(entry.summary or entry.description, terms),
                score=_score(
                    terms,
                    key=entry.key,
                    title=entry.title,
                    body=f"{entry.summary} {entry.description} {entry.real_world_usage}",
                    keywords=entry.keywords,
                ),
                url=f"/reference/{entry.key}",
                meta={"module": entry.module, "signature": entry.signature, "kind": entry.kind},
            )
            for entry in rows
        ]

    def _search_lessons(self, terms: list[str]) -> list[SearchHit]:
        rows = self._session.scalars(
            select(Lesson).where(
                or_(
                    self._like_clauses(Lesson.title, terms),
                    self._like_clauses(Lesson.summary, terms),
                    self._like_clauses(Lesson.body, terms),
                )
            )
        ).all()
        return [
            SearchHit(
                kind="lesson",
                slug=lesson.slug,
                title=lesson.title,
                snippet=_snippet(lesson.summary or lesson.body, terms),
                score=_score(
                    terms,
                    key=lesson.slug,
                    title=lesson.title,
                    body=f"{lesson.summary} {lesson.body}",
                    keywords=lesson.reference_keys,
                )
                * 1.1,  # lessons are the primary teaching surface
                url=f"/learn/{lesson.slug}",
                meta={"level": lesson.level, "minutes": lesson.estimated_minutes},
            )
            for lesson in rows
        ]

    def _search_concepts(self, terms: list[str]) -> list[SearchHit]:
        rows = self._session.scalars(
            select(Concept).where(
                or_(
                    self._like_clauses(Concept.slug, terms),
                    self._like_clauses(Concept.name, terms),
                    self._like_clauses(Concept.description, terms),
                )
            )
        ).all()
        return [
            SearchHit(
                kind="concept",
                slug=concept.slug,
                title=concept.name,
                snippet=_snippet(concept.description, terms),
                score=_score(
                    terms,
                    key=concept.slug,
                    title=concept.name,
                    body=concept.description,
                    keywords=[concept.category],
                ),
                url=f"/progress/concepts/{concept.slug}",
                meta={"level": concept.level, "category": concept.category},
            )
            for concept in rows
        ]

    def _search_exercises(self, terms: list[str]) -> list[SearchHit]:
        rows = self._session.scalars(
            select(Exercise).where(
                or_(
                    self._like_clauses(Exercise.title, terms),
                    self._like_clauses(Exercise.prompt, terms),
                )
            )
        ).all()
        return [
            SearchHit(
                kind="exercise",
                slug=exercise.slug,
                title=exercise.title,
                snippet=_snippet(exercise.prompt, terms),
                score=_score(
                    terms,
                    key=exercise.slug,
                    title=exercise.title,
                    body=exercise.prompt,
                    keywords=exercise.concept_slugs,
                )
                * 0.9,
                url=f"/practice/{exercise.slug}",
                meta={"kind": exercise.kind, "level": exercise.level},
            )
            for exercise in rows
        ]

    def _search_projects(self, terms: list[str]) -> list[SearchHit]:
        rows = self._session.scalars(
            select(Project).where(
                or_(
                    self._like_clauses(Project.title, terms),
                    self._like_clauses(Project.tagline, terms),
                    self._like_clauses(Project.requirements, terms),
                )
            )
        ).all()
        return [
            SearchHit(
                kind="project",
                slug=project.slug,
                title=project.title,
                snippet=_snippet(project.tagline or project.requirements, terms),
                score=_score(
                    terms,
                    key=project.slug,
                    title=project.title,
                    body=f"{project.tagline} {project.requirements}",
                    keywords=project.concept_slugs,
                ),
                url=f"/projects/{project.slug}",
                meta={"level": project.level, "guidance": project.guidance},
            )
            for project in rows
        ]
