"""SQLAlchemy models.

Importing this package registers every mapped class with :class:`Base.metadata`,
which is what Alembic autogeneration and ``create_all`` rely on. Import models
from here (``from app.models import User``) rather than from submodules.
"""

from app.models.achievement import Achievement, Certification, UserAchievement
from app.models.ai import AIConversation, AIMessage
from app.models.curriculum import (
    Concept,
    Course,
    Lesson,
    Module,
    concept_prerequisites,
    lesson_concepts,
)
from app.models.enums import (
    AIMode,
    CertificationLevel,
    ChallengeKind,
    ExecutionMode,
    ExerciseKind,
    GraderKind,
    GuidanceLevel,
    LearningEventKind,
    SkillLevel,
    SubmissionStatus,
    UserRole,
)
from app.models.exercise import Exercise, Hint, QuizQuestion
from app.models.mastery import ConceptMastery, LearningEvent, LessonProgress
from app.models.project import Project, ProjectSubmission, ProjectWorkspace
from app.models.reference import ReferenceEntry
from app.models.submission import ExecutionRun, HintReveal, SavedSnippet, Submission
from app.models.user import User

__all__ = [
    "AIConversation",
    "AIMessage",
    "AIMode",
    "Achievement",
    "CertificationLevel",
    "Certification",
    "ChallengeKind",
    "Concept",
    "ConceptMastery",
    "Course",
    "ExecutionMode",
    "ExecutionRun",
    "Exercise",
    "ExerciseKind",
    "GraderKind",
    "GuidanceLevel",
    "Hint",
    "HintReveal",
    "LearningEvent",
    "LearningEventKind",
    "Lesson",
    "LessonProgress",
    "Module",
    "Project",
    "ProjectSubmission",
    "ProjectWorkspace",
    "QuizQuestion",
    "ReferenceEntry",
    "SavedSnippet",
    "SkillLevel",
    "Submission",
    "SubmissionStatus",
    "User",
    "UserAchievement",
    "UserRole",
    "concept_prerequisites",
    "lesson_concepts",
]
