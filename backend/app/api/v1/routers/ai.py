"""AI tutor endpoints."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.db.base import utcnow
from app.models import AIConversation, AIMessage
from app.schemas.learning import (
    AIMessageResponse,
    AIStatusResponse,
    ConversationDetail,
    ConversationSummary,
    SendMessageRequest,
    StartConversationRequest,
)
from app.services.ai_tutor import AITutorService

router = APIRouter(prefix="/ai", tags=["ai-tutor"])


@router.get("/status", response_model=AIStatusResponse, summary="Tutor availability")
def ai_status(user: CurrentUser, session: DbSession) -> AIStatusResponse:
    """Whether a live model backs the tutor, and today's remaining allowance."""
    settings = get_settings()
    since = utcnow() - timedelta(days=1)
    used = int(
        session.scalar(
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
    return AIStatusResponse(
        backend="anthropic" if settings.ai_enabled else "offline",
        model=settings.ai_model if settings.ai_enabled else None,
        live=settings.ai_enabled,
        daily_limit=settings.ai_daily_message_limit,
        used_today=used,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
    summary="List tutoring threads",
)
def list_conversations(user: CurrentUser, session: DbSession) -> list[ConversationSummary]:
    """Recent tutoring threads."""
    return [
        ConversationSummary.model_validate(conversation)
        for conversation in AITutorService(session).conversations(user.id)
    ]


@router.post(
    "/conversations",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Start a tutoring thread",
)
def start_conversation(
    payload: StartConversationRequest, user: CurrentUser, session: DbSession
) -> ConversationDetail:
    """Open a new thread, optionally pinned to a lesson or exercise."""
    context: dict[str, str] = {}
    if payload.lesson_slug:
        context["lesson_slug"] = payload.lesson_slug
    if payload.exercise_slug:
        context["exercise_slug"] = payload.exercise_slug

    conversation = AITutorService(session).start_conversation(
        user, mode=payload.mode, title=payload.title, context=context
    )
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        mode=conversation.mode,
        context=conversation.context,
        hint_level_reached=conversation.hint_level_reached,
        updated_at=conversation.updated_at,
        messages=[],
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Read a thread",
)
def get_conversation(
    conversation_id: str, user: CurrentUser, session: DbSession
) -> ConversationDetail:
    """Return a thread with all of its turns."""
    conversation = session.get(AIConversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise NotFoundError("Conversation", conversation_id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        mode=conversation.mode,
        context=conversation.context,
        hint_level_reached=conversation.hint_level_reached,
        updated_at=conversation.updated_at,
        messages=[AIMessageResponse.model_validate(message) for message in conversation.messages],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AIMessageResponse,
    summary="Send a message to the tutor",
)
def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    user: CurrentUser,
    session: DbSession,
) -> AIMessageResponse:
    """Send a turn and receive the tutor's reply.

    While the learner has an unsolved exercise open, the tutor's system prompt
    forbids revealing a working solution; the policy is rebuilt server-side on
    every call from persisted state.
    """
    _, assistant = AITutorService(session).send(
        user,
        conversation_id,
        payload.message,
        mode=payload.mode,
        code=payload.code,
        error_output=payload.error_output,
    )
    return AIMessageResponse.model_validate(assistant)


@router.delete("/conversations/{conversation_id}", summary="Delete a thread")
def delete_conversation(
    conversation_id: str, user: CurrentUser, session: DbSession
) -> dict[str, str]:
    """Remove a tutoring thread and its messages."""
    conversation = session.get(AIConversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise NotFoundError("Conversation", conversation_id)
    session.delete(conversation)
    return {"message": "Conversation deleted."}
