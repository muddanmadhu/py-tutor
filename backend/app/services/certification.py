"""Certification: gating awards on demonstrated mastery.

Each certification declares required concept categories with a minimum mastery
score, a minimum number of mastered concepts, and required project verdicts.
Nothing is awarded on lesson completion or XP alone — those are effort metrics,
and a certificate that tracks effort is worthless to the person reading it.

Requirements are checked on demand and the evidence is snapshotted onto the
award, so a certificate can always be explained after the fact.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailure
from app.db.base import utcnow
from app.models import Certification, Project, ProjectSubmission, User
from app.models.enums import CertificationLevel, LearningEventKind
from app.services import analytics
from app.services.mastery import MasteryService


@dataclass(frozen=True, slots=True)
class CertificationRequirement:
    """What a learner must demonstrate to earn one certification."""

    level: CertificationLevel
    title: str
    description: str
    #: Concept categories that must reach ``category_threshold`` on average.
    required_categories: tuple[str, ...]
    category_threshold: float
    #: Minimum count of concepts at mastered status.
    min_mastered_concepts: int
    #: Project slugs that must have a passing submission.
    required_projects: tuple[str, ...]
    #: Minimum overall curriculum mastery.
    min_overall_mastery: float


REQUIREMENTS: tuple[CertificationRequirement, ...] = (
    CertificationRequirement(
        level=CertificationLevel.FOUNDATIONS,
        title="Python Foundations",
        description="Can write correct small programs with variables, conditions, loops "
        "and collections.",
        required_categories=("fundamentals", "control-flow"),
        category_threshold=0.75,
        min_mastered_concepts=6,
        required_projects=(),
        min_overall_mastery=0.15,
    ),
    CertificationRequirement(
        level=CertificationLevel.DEVELOPER,
        title="Python Developer",
        description="Writes functions, classes and modules; handles errors and files; "
        "ships a working application.",
        required_categories=("fundamentals", "functions", "collections", "errors"),
        category_threshold=0.75,
        min_mastered_concepts=14,
        required_projects=("expense-tracker-cli",),
        min_overall_mastery=0.35,
    ),
    CertificationRequirement(
        level=CertificationLevel.ADVANCED_DEVELOPER,
        title="Advanced Python Developer",
        description="Commands decorators, generators, context managers, typing and the "
        "object model.",
        required_categories=("functions", "oop", "advanced"),
        category_threshold=0.8,
        min_mastered_concepts=22,
        required_projects=("expense-tracker-cli",),
        min_overall_mastery=0.5,
    ),
    CertificationRequirement(
        level=CertificationLevel.AUTOMATION_ENGINEER,
        title="Python Automation Engineer",
        description="Automates real systems: files, APIs, data formats and scheduled work.",
        required_categories=("files", "apis", "automation"),
        category_threshold=0.78,
        min_mastered_concepts=20,
        required_projects=("file-processing-platform",),
        min_overall_mastery=0.5,
    ),
    CertificationRequirement(
        level=CertificationLevel.BACKEND_DEVELOPER,
        title="Python Backend Developer",
        description="Builds and operates HTTP services backed by a database.",
        required_categories=("apis", "databases", "testing"),
        category_threshold=0.78,
        min_mastered_concepts=24,
        required_projects=("enterprise-automation-service",),
        min_overall_mastery=0.55,
    ),
    CertificationRequirement(
        level=CertificationLevel.TEST_AUTOMATION_ENGINEER,
        title="Python Test Automation Engineer",
        description="Designs test architecture, writes suites that find real defects, and "
        "debugs failures systematically.",
        required_categories=("testing", "debugging"),
        category_threshold=0.82,
        min_mastered_concepts=18,
        required_projects=(),
        min_overall_mastery=0.5,
    ),
    CertificationRequirement(
        level=CertificationLevel.ENGINEERING_MASTER,
        title="Python Engineering Master",
        description="Takes a business requirement and delivers a designed, tested, secured, "
        "documented and deployable Python system.",
        required_categories=(
            "fundamentals",
            "functions",
            "oop",
            "advanced",
            "apis",
            "databases",
            "testing",
            "automation",
        ),
        category_threshold=0.85,
        min_mastered_concepts=35,
        required_projects=("enterprise-automation-service",),
        min_overall_mastery=0.75,
    ),
)

REQUIREMENTS_BY_LEVEL = {requirement.level: requirement for requirement in REQUIREMENTS}


@dataclass(frozen=True, slots=True)
class CertificationStatus:
    """Whether one certification is earned, and what is still missing."""

    level: CertificationLevel
    title: str
    description: str
    earned: bool
    eligible: bool
    progress: float
    unmet: list[str]
    evidence: dict[str, Any]
    awarded_at: str | None = None
    certificate_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the API."""
        return {
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "earned": self.earned,
            "eligible": self.eligible,
            "progress": round(self.progress, 4),
            "unmet_requirements": self.unmet,
            "evidence": self.evidence,
            "awarded_at": self.awarded_at,
            "certificate_code": self.certificate_code,
        }


class CertificationService:
    """Evaluates and awards certifications."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mastery = MasteryService(session)

    def status_for(self, user: User) -> list[CertificationStatus]:
        """Status of every certification track for one learner."""
        views = self._mastery.view_for(user.id)
        overall = self._mastery.overall_mastery(user.id)
        mastered_count = sum(1 for view in views if view.is_mastered)
        by_category: dict[str, list[float]] = {}
        for view in views:
            by_category.setdefault(view.category, []).append(view.score)

        passed_projects = set(
            self._session.scalars(
                select(Project.slug)
                .join(ProjectSubmission, ProjectSubmission.project_id == Project.id)
                .where(
                    ProjectSubmission.user_id == user.id,
                    ProjectSubmission.verdict == "passed",
                )
            ).all()
        )
        awarded = {
            record.level: record
            for record in self._session.scalars(
                select(Certification).where(Certification.user_id == user.id)
            ).all()
        }

        statuses: list[CertificationStatus] = []
        for requirement in REQUIREMENTS:
            unmet: list[str] = []
            satisfied = 0
            total_checks = (
                len(requirement.required_categories) + 2 + len(requirement.required_projects)
            )

            category_averages: dict[str, float] = {}
            for category in requirement.required_categories:
                scores = by_category.get(category, [])
                average = sum(scores) / len(scores) if scores else 0.0
                category_averages[category] = round(average, 4)
                if average >= requirement.category_threshold:
                    satisfied += 1
                else:
                    needed = round(requirement.category_threshold * 100)
                    unmet.append(
                        f"{category.replace('-', ' ').title()} mastery is "
                        f"{round(average * 100)}%, needs {needed}%"
                    )

            if mastered_count >= requirement.min_mastered_concepts:
                satisfied += 1
            else:
                unmet.append(
                    f"{mastered_count} concepts mastered, needs {requirement.min_mastered_concepts}"
                )

            if overall >= requirement.min_overall_mastery:
                satisfied += 1
            else:
                unmet.append(
                    f"Overall mastery is {round(overall * 100)}%, needs "
                    f"{round(requirement.min_overall_mastery * 100)}%"
                )

            for project_slug in requirement.required_projects:
                if project_slug in passed_projects:
                    satisfied += 1
                else:
                    unmet.append(f"Project '{project_slug}' not yet passed")

            record = awarded.get(requirement.level.value)
            statuses.append(
                CertificationStatus(
                    level=requirement.level,
                    title=requirement.title,
                    description=requirement.description,
                    earned=record is not None,
                    eligible=not unmet,
                    progress=satisfied / total_checks if total_checks else 0.0,
                    unmet=unmet,
                    evidence={
                        "overall_mastery": overall,
                        "concepts_mastered": mastered_count,
                        "category_averages": category_averages,
                        "projects_passed": sorted(passed_projects),
                    },
                    awarded_at=record.awarded_at.isoformat() if record else None,
                    certificate_code=record.certificate_code if record else None,
                )
            )
        return statuses

    def claim(self, user: User, level: CertificationLevel) -> Certification:
        """Award a certification the learner has earned.

        Raises
        ------
        ValidationFailure
            If the requirements are not met, listing exactly what is missing.
        """
        status = next((item for item in self.status_for(user) if item.level is level), None)
        if status is None:
            raise ValidationFailure(f"Unknown certification: {level}")
        if status.earned:
            existing = self._session.scalar(
                select(Certification).where(
                    Certification.user_id == user.id, Certification.level == level.value
                )
            )
            if existing:
                return existing
        if not status.eligible:
            raise ValidationFailure(
                "You haven't demonstrated everything this certification requires yet.",
                details={"unmet_requirements": status.unmet},
            )

        certification = Certification(
            user_id=user.id,
            level=level.value,
            awarded_at=utcnow(),
            evidence=status.evidence,
            overall_mastery=float(status.evidence.get("overall_mastery", 0.0)),
            certificate_code=_certificate_code(user.id, level.value),
        )
        self._session.add(certification)
        analytics.record_event(
            self._session,
            user,
            LearningEventKind.CERTIFICATION_EARNED,
            subject_type="certification",
            subject_slug=level.value,
            payload=status.evidence,
        )
        self._session.flush()
        return certification


def _certificate_code(user_id: str, level: str) -> str:
    """Deterministic, verifiable certificate identifier."""
    digest = hashlib.sha256(f"{user_id}:{level}".encode()).hexdigest()[:16].upper()
    return f"PF-{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"
