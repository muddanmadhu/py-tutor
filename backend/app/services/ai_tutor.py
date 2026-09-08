"""The AI tutor.

Two things make this more than a chat wrapper.

**A hint ladder that is enforced, not suggested.** While a learner has an
unsolved exercise open, the tutor operates under a policy that forbids handing
over working code. The rung the learner has reached is server-side state, and
the system prompt is rebuilt from it on every turn — a learner cannot talk the
tutor into skipping ahead, because the instruction to withhold is not in the
conversation the learner can influence.

**A deterministic fallback.** With no API key configured the platform still
tutors: :class:`OfflineTutor` composes responses from the authored hints, the
static code-review engine and the error interpreter. The platform is never
dead without a model.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AIUnavailableError, NotFoundError
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models import AIConversation, AIMessage, Exercise, Hint, Lesson, Submission, User
from app.models.enums import AIMode, LearningEventKind, SubmissionStatus
from app.services import analytics
from app.services.code_review import review_files
from app.services.grading import interpret_traceback

logger = get_logger(__name__)

MAX_HINT_LEVEL = 4
#: Turns of history sent to the model. Older turns are summarised out.
HISTORY_WINDOW = 12


@dataclass(frozen=True, slots=True)
class TutorContext:
    """What the learner is working on right now."""

    lesson_slug: str | None = None
    exercise_slug: str | None = None
    code: str | None = None
    error_output: str | None = None
    hint_level: int = 0
    exercise_solved: bool = False
    exercise_prompt: str | None = None
    authored_hints: tuple[str, ...] = ()
    reference_solution: str | None = None

    @property
    def practising(self) -> bool:
        """Whether solution-withholding rules apply."""
        return bool(self.exercise_slug) and not self.exercise_solved


@dataclass(frozen=True, slots=True)
class TutorReply:
    """One tutor turn."""

    content: str
    hint_level: int
    withheld_solution: bool
    model: str
    usage: dict[str, Any]


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------

_BASE_PERSONA = """\
You are the PyForge tutor: a patient, precise senior Python engineer mentoring a learner
inside an interactive platform.

How you teach:
- Answer the question that was asked, at the learner's level.
- Prefer a worked reason over an assertion: show *why* Python behaves this way.
- Use short code fragments to illustrate mechanics. Runnable snippets are welcome for
  *concepts*; complete solutions to the learner's current exercise are not.
- When the learner is wrong, say so plainly and show the evidence, then help them fix it.
- Never invent Python behaviour. If you are unsure, say what you would check and how.
- Keep answers tight. Two focused paragraphs beat ten unfocused ones.
"""

_PRACTISING_POLICY = """\
CURRENT SITUATION: the learner has an UNSOLVED exercise open.

Non-negotiable rules for this turn:
1. Do NOT write the solution, or any code that could be pasted in to pass the exercise.
2. Do NOT write the body of the function or algorithm they were asked to write.
3. You MAY explain concepts, show *analogous* examples on different data, ask questions,
   point at the specific line that is wrong, and explain an error message in full.
4. If the learner asks outright for the answer, decline in one sentence, without
   moralising, and give them the next rung of help instead.

They are currently at hint level {hint_level} of {max_level}. Give help at that rung:
  level 1 — a conceptual clue: which idea applies, and why it applies here
  level 2 — a direction: the shape of the approach, in words, no code
  level 3 — a specific area: which line or expression is wrong, and what is wrong about it
  level 4 — a partial solution: structure or pseudocode with the key step left to them

Do not exceed the current rung, even if asked.
"""

_SOLVED_POLICY = """\
CURRENT SITUATION: the learner has already solved this exercise, so you may discuss the
solution freely. Focus on alternatives, trade-offs, performance and idiom.
"""

_MODE_INSTRUCTIONS: dict[AIMode, str] = {
    AIMode.EXPLAIN_CODE: (
        "Walk through the code the learner supplied, in execution order. Name the mechanism "
        "behind each step, not just its effect. Finish with what the code does as a whole."
    ),
    AIMode.EXPLAIN_ERROR: (
        "Explain the error. Structure it as: what Python is complaining about, why it "
        "happened in *this* code, how to read this kind of traceback in future, and how to "
        "fix the category of mistake (not just this instance)."
    ),
    AIMode.HINT: "Give exactly one hint at the learner's current rung. Nothing beyond it.",
    AIMode.SOCRATIC: (
        "Do not explain. Ask one question at a time that makes the learner notice the thing "
        "they have missed. Wait for their answer before the next question."
    ),
    AIMode.REVIEW: (
        "Review the code as a senior engineer would in a pull request: correctness first, "
        "then readability, maintainability, error handling, security and performance. Be "
        "concrete and cite line numbers. Say what is good as well as what is not."
    ),
    AIMode.GENERATE_EXERCISE: (
        "Write a new practice exercise on the requested topic. Include: the brief, a "
        "worked example of the expected input/output, and the pytest suite that grades it. "
        "Do not include the solution."
    ),
    AIMode.GENERATE_TESTS: (
        "Write a pytest suite for the code supplied. Cover the happy path, boundaries, and "
        "the failure modes the code actually has. Name each test after the behaviour it "
        "pins down."
    ),
    AIMode.MOCK_INTERVIEW: (
        "Conduct a technical interview. Ask one question, wait for the answer, then probe "
        "the reasoning before moving on. Grade at the end against: correctness, "
        "communication, Python idiom, and awareness of trade-offs."
    ),
    AIMode.FREEFORM: "",
}


def build_system_prompt(mode: AIMode, context: TutorContext) -> str:
    """Assemble the system prompt from the persona, policy and mode."""
    parts = [_BASE_PERSONA]

    if context.practising:
        parts.append(
            _PRACTISING_POLICY.format(
                hint_level=max(1, context.hint_level), max_level=MAX_HINT_LEVEL
            )
        )
    elif context.exercise_slug:
        parts.append(_SOLVED_POLICY)

    instruction = _MODE_INSTRUCTIONS.get(mode, "")
    if instruction:
        parts.append(f"MODE: {mode.value}\n{instruction}")

    if context.exercise_prompt:
        parts.append(f"THE EXERCISE BRIEF:\n{context.exercise_prompt}")
    if context.authored_hints and context.practising:
        rungs = "\n".join(
            f"  level {index + 1}: {text}"
            for index, text in enumerate(context.authored_hints[: context.hint_level or 1])
        )
        parts.append(
            "HINTS THE LEARNER HAS ALREADY UNLOCKED (do not repeat them verbatim; build on "
            f"them):\n{rungs}"
        )
    if context.code:
        parts.append(f"THE LEARNER'S CURRENT CODE:\n```python\n{context.code[:6000]}\n```")
    if context.error_output:
        parts.append(f"THE ERROR THEY ARE SEEING:\n```\n{context.error_output[:3000]}\n```")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


class TutorBackend(Protocol):
    """Generates a tutor reply from a system prompt and conversation history."""

    name: str

    def generate(
        self, system_prompt: str, history: list[dict[str, str]], context: TutorContext
    ) -> TutorReply:
        """Produce one reply."""
        ...


class OfflineTutor:
    """Deterministic tutor used when no model is configured.

    It is genuinely useful rather than a stub: it explains tracebacks using the
    same interpreter the grader uses, runs the static review engine over the
    learner's code, and serves the authored hint ladder.
    """

    name = "offline"

    def generate(
        self,
        system_prompt: str,  # noqa: ARG002 - policy is applied directly, not via a prompt
        history: list[dict[str, str]],
        context: TutorContext,
    ) -> TutorReply:
        """Compose a reply from the deterministic engines."""
        question = history[-1]["content"] if history else ""
        sections: list[str] = []

        if context.error_output:
            _, explanation = interpret_traceback(context.error_output)
            if explanation:
                sections.append(f"### What the error means\n\n{explanation}")

        if context.practising:
            rung = min(max(1, context.hint_level or 1), MAX_HINT_LEVEL)
            if context.authored_hints and rung <= len(context.authored_hints):
                sections.append(
                    f"### Hint {rung} of {MAX_HINT_LEVEL}\n\n{context.authored_hints[rung - 1]}"
                )
            else:
                sections.append(
                    f"### Hint {rung}\n\n{_GENERIC_HINTS[min(rung, len(_GENERIC_HINTS)) - 1]}"
                )

        if context.code and not context.practising:
            result = review_files({"main.py": context.code})
            if result.findings:
                bullets = "\n".join(
                    f"- **{f.severity.value}** (line {f.line or '?'}): {f.message} _{f.suggestion}_"
                    for f in result.findings[:6]
                )
                sections.append(f"### Review of your code\n\n{bullets}")
            if result.strengths:
                sections.append(
                    "### What's working\n\n"
                    + "\n".join(f"- {strength}" for strength in result.strengths)
                )

        if not sections:
            sections.append(
                textwrap.dedent(
                    f"""\
                    The AI tutor is running in offline mode, so I can't answer free-form
                    questions right now — but the platform's deterministic help still works:

                    - **Stuck on an exercise?** Use the Hint button to walk the hint ladder.
                    - **Got an error?** Paste the traceback here and I'll explain it.
                    - **Want feedback on your code?** Use *Review* on any submission.

                    You asked: *{question[:200]}*
                    Try the Python Reference for that — search it from the top bar.
                    """
                )
            )

        return TutorReply(
            content="\n\n".join(sections),
            hint_level=context.hint_level,
            withheld_solution=context.practising,
            model="offline",
            usage={},
        )


_GENERIC_HINTS = [
    "Start from the requirement, not the code. Write one sentence describing exactly what "
    "the program must output for a given input. Most stuck exercises are unclear briefs, "
    "not hard code.",
    "Break the task into three steps and name them. Which of the three does your code not do yet?",
    "Add a `print()` on the line just before the part you're unsure about, and run it. "
    "Compare what you see with what you expected — the gap is the bug.",
    "Write the structure first, with `pass` in the middle: the function signature, the loop, "
    "the return. Then fill in the one step you actually need to think about.",
]


class AnthropicTutor:
    """Model-backed tutor using the Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise AIUnavailableError(
                "The AI tutor requires the 'anthropic' package. Install with: pip install "
                "'pyforge[ai]'"
            ) from exc
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.ai_request_timeout_seconds,
        )

    def generate(
        self, system_prompt: str, history: list[dict[str, str]], context: TutorContext
    ) -> TutorReply:
        """Call the model and return its reply."""
        # Typed as Any because the SDK's MessageParam is a TypedDict with a
        # Literal role, and importing its types here would make the optional
        # `anthropic` dependency load-bearing for type checking.
        messages: Any = [
            {"role": turn["role"], "content": turn["content"]} for turn in history[-HISTORY_WINDOW:]
        ]
        try:
            response = self._client.messages.create(
                model=self._settings.ai_model,
                max_tokens=self._settings.ai_max_tokens,
                system=system_prompt,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001 - vendor SDK raises a wide family
            logger.exception("AI tutor request failed")
            raise AIUnavailableError(
                "The AI tutor is temporarily unavailable. The hint ladder and code review "
                "still work."
            ) from exc

        # Content blocks are a wide union (thinking, tool use, …); only text
        # blocks carry `.text`, so read it defensively rather than by attribute.
        text = "".join(
            str(getattr(block, "text", ""))
            for block in response.content
            if getattr(block, "type", "") == "text"
        )
        return TutorReply(
            content=text.strip() or "(no response)",
            hint_level=context.hint_level,
            withheld_solution=context.practising,
            model=self._settings.ai_model,
            usage={
                "input_tokens": getattr(response.usage, "input_tokens", 0),
                "output_tokens": getattr(response.usage, "output_tokens", 0),
            },
        )


def get_backend(settings: Settings | None = None) -> TutorBackend:
    """Return the configured tutor backend."""
    settings = settings or get_settings()
    if settings.ai_enabled:
        try:
            return AnthropicTutor(settings)
        except AIUnavailableError:
            logger.warning("falling back to the offline tutor")
    return OfflineTutor()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AITutorService:
    """Conversation management, policy assembly and quota enforcement."""

    def __init__(self, session: Session, backend: TutorBackend | None = None) -> None:
        self._session = session
        self._settings = get_settings()
        self._backend = backend or get_backend(self._settings)

    def start_conversation(
        self,
        user: User,
        *,
        mode: AIMode = AIMode.FREEFORM,
        title: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AIConversation:
        """Create a new tutoring thread."""
        conversation = AIConversation(
            user_id=user.id,
            title=title or _default_title(mode),
            mode=mode.value,
            context=context or {},
        )
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def send(
        self,
        user: User,
        conversation_id: str,
        message: str,
        *,
        mode: AIMode | None = None,
        code: str | None = None,
        error_output: str | None = None,
    ) -> tuple[AIMessage, AIMessage]:
        """Append the learner's message, generate a reply, and persist both."""
        conversation = self._session.get(AIConversation, conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise NotFoundError("Conversation", conversation_id)

        self._enforce_daily_quota(user)

        effective_mode = mode or AIMode(conversation.mode)
        context = self._build_context(user, conversation, code, error_output)

        # Snapshot the history *before* persisting the new turn: appending first
        # and then reading `conversation.messages` would include it twice, since
        # the lazy load happens after the flush.
        history = [
            {"role": turn.role, "content": turn.content}
            for turn in conversation.messages
            if turn.role in {"user", "assistant"}
        ]
        history.append({"role": "user", "content": message.strip()})

        user_message = AIMessage(
            conversation_id=conversation.id, role="user", content=message.strip()
        )
        self._session.add(user_message)
        self._session.flush()

        system_prompt = build_system_prompt(effective_mode, context)
        reply = self._backend.generate(system_prompt, history, context)

        assistant_message = AIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=reply.content,
            meta={
                "model": reply.model,
                "mode": effective_mode.value,
                "hint_level": reply.hint_level,
                "withheld_solution": reply.withheld_solution,
                "usage": reply.usage,
            },
        )
        self._session.add(assistant_message)
        conversation.hint_level_reached = max(conversation.hint_level_reached, reply.hint_level)
        if conversation.title == _default_title(AIMode.FREEFORM):
            conversation.title = message.strip()[:80] or conversation.title

        analytics.record_event(
            self._session,
            user,
            LearningEventKind.AI_MESSAGE_SENT,
            subject_type="conversation",
            subject_slug=conversation.id,
            payload={"mode": effective_mode.value, "model": reply.model},
        )
        self._session.flush()
        return user_message, assistant_message

    def conversations(self, user_id: str, limit: int = 30) -> list[AIConversation]:
        """Recent threads, newest first."""
        return list(
            self._session.scalars(
                select(AIConversation)
                .where(AIConversation.user_id == user_id)
                .order_by(AIConversation.updated_at.desc())
                .limit(limit)
            ).all()
        )

    # -- internals ----------------------------------------------------------

    def _enforce_daily_quota(self, user: User) -> None:
        since = utcnow() - timedelta(days=1)
        used = int(
            self._session.scalar(
                select(func.count())
                .select_from(AIMessage)
                .join(AIConversation, AIConversation.id == AIMessage.conversation_id)
                .where(
                    AIConversation.user_id == user.id,
                    AIMessage.role == "user",
                    AIMessage.created_at >= since,
                )
            )
            or 0
        )
        if used >= self._settings.ai_daily_message_limit:
            raise AIUnavailableError(
                f"You've reached today's tutor limit of {self._settings.ai_daily_message_limit} "
                "messages. The hint ladder, code review and reference are still available."
            )

    def _build_context(
        self,
        user: User,
        conversation: AIConversation,
        code: str | None,
        error_output: str | None,
    ) -> TutorContext:
        """Reconstruct the policy context from server-side state.

        Everything that governs what the tutor may reveal is read from the
        database here, never taken from the request body.
        """
        exercise_slug = conversation.context.get("exercise_slug")
        lesson_slug = conversation.context.get("lesson_slug")
        if not exercise_slug:
            return TutorContext(lesson_slug=lesson_slug, code=code, error_output=error_output)

        exercise = self._session.scalar(select(Exercise).where(Exercise.slug == str(exercise_slug)))
        if exercise is None:
            return TutorContext(lesson_slug=lesson_slug, code=code, error_output=error_output)

        solved = bool(
            self._session.scalar(
                select(Submission.id).where(
                    Submission.user_id == user.id,
                    Submission.exercise_id == exercise.id,
                    Submission.status == SubmissionStatus.PASSED.value,
                )
            )
        )
        hints = list(
            self._session.scalars(
                select(Hint).where(Hint.exercise_id == exercise.id).order_by(Hint.level)
            ).all()
        )
        revealed = self._revealed_hint_level(user.id, exercise.id)

        lesson = (
            self._session.scalar(select(Lesson).where(Lesson.slug == str(lesson_slug)))
            if lesson_slug
            else None
        )
        return TutorContext(
            lesson_slug=lesson.slug if lesson else lesson_slug,
            exercise_slug=exercise.slug,
            code=code,
            error_output=error_output,
            hint_level=max(1, revealed) if not solved else 0,
            exercise_solved=solved,
            exercise_prompt=exercise.prompt,
            authored_hints=tuple(hint.text for hint in hints),
            reference_solution=None,  # never placed in the prompt while practising
        )

    def _revealed_hint_level(self, user_id: str, exercise_id: str) -> int:
        from app.models import HintReveal

        return int(
            self._session.scalar(
                select(func.coalesce(func.max(HintReveal.level), 0)).where(
                    HintReveal.user_id == user_id,
                    HintReveal.exercise_id == exercise_id,
                    HintReveal.source == "authored",
                )
            )
            or 0
        )


def _default_title(mode: AIMode) -> str:
    return {
        AIMode.EXPLAIN_CODE: "Explain this code",
        AIMode.EXPLAIN_ERROR: "What does this error mean?",
        AIMode.HINT: "I need a hint",
        AIMode.SOCRATIC: "Socratic session",
        AIMode.REVIEW: "Code review",
        AIMode.GENERATE_EXERCISE: "Generate an exercise",
        AIMode.GENERATE_TESTS: "Generate tests",
        AIMode.MOCK_INTERVIEW: "Mock interview",
    }.get(mode, "New conversation")
