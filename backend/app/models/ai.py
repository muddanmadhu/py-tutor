"""AI tutor conversation persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AIMode

if TYPE_CHECKING:
    from app.models.user import User


class AIConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tutoring thread.

    ``context`` pins the conversation to what the learner is working on
    (lesson, exercise, current code). The tutor policy uses it to decide how
    much it is allowed to reveal — see :mod:`app.services.ai_tutor`.
    """

    __tablename__ = "ai_conversations"
    __table_args__ = (Index("ix_ai_conversations_user_id_updated_at", "user_id", "updated_at"),)

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), default="New conversation", nullable=False)
    mode: Mapped[str] = mapped_column(String(24), default=AIMode.FREEFORM, nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    #: How far up the hint ladder this thread has already gone.
    hint_level_reached: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[AIMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AIMessage.created_at",
        passive_deletes=True,
    )


class AIMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One turn in a tutoring thread."""

    __tablename__ = "ai_messages"
    __table_args__ = (
        Index("ix_ai_messages_conversation_id_created_at", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: Model id, token usage and policy decisions, for cost and audit review.
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    conversation: Mapped[AIConversation] = relationship(back_populates="messages")
