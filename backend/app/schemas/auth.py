"""Authentication and user schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import EmailStr, Field

from app.models.enums import SkillLevel
from app.schemas.common import APIModel


class RegisterRequest(APIModel):
    """New account details."""

    email: EmailStr
    password: Annotated[str, Field(min_length=10, max_length=200)]
    display_name: Annotated[str, Field(min_length=1, max_length=80)]
    declared_level: SkillLevel = SkillLevel.BEGINNER
    goal: Annotated[str | None, Field(max_length=200)] = None


class LoginRequest(APIModel):
    """Credentials."""

    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=200)]


class RefreshRequest(APIModel):
    """Refresh-token exchange."""

    refresh_token: str


class ChangePasswordRequest(APIModel):
    """Password rotation."""

    current_password: str
    new_password: Annotated[str, Field(min_length=10, max_length=200)]


class TokenResponse(APIModel):
    """Issued credentials."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - the OAuth2 scheme name, not a credential
    expires_in_seconds: int


class UserResponse(APIModel):
    """A user profile."""

    id: str
    email: str
    display_name: str
    role: str
    declared_level: str
    goal: str | None
    xp: int
    streak_days: int
    longest_streak_days: int
    last_active_on: date | None
    total_coding_seconds: int
    preferences: dict[str, Any]
    created_at: datetime


class UpdateProfileRequest(APIModel):
    """Editable profile fields."""

    display_name: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    declared_level: SkillLevel | None = None
    goal: Annotated[str | None, Field(max_length=200)] = None
    active_course_slug: Annotated[str | None, Field(max_length=120)] = None
    preferences: dict[str, Any] | None = None


class AuthResponse(APIModel):
    """Login/registration response: profile plus credentials."""

    user: UserResponse
    tokens: TokenResponse
