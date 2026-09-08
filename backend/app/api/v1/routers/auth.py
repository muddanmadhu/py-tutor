"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.core.security import TokenError, TokenType, decode_token
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    tokens = AuthService.issue_tokens(user)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in_seconds=get_settings().access_token_ttl_minutes * 60,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a learner account",
)
def register(payload: RegisterRequest, session: DbSession) -> AuthResponse:
    """Register a new learner and return credentials."""
    user = AuthService(session).register(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        declared_level=payload.declared_level,
        goal=payload.goal,
    )
    return AuthResponse(user=UserResponse.model_validate(user), tokens=_token_response(user))


@router.post("/login", response_model=AuthResponse, summary="Exchange credentials for tokens")
def login(payload: LoginRequest, session: DbSession) -> AuthResponse:
    """Authenticate and return credentials."""
    user = AuthService(session).authenticate(payload.email, payload.password)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=_token_response(user))


@router.post("/refresh", response_model=TokenResponse, summary="Refresh an access token")
def refresh(payload: RefreshRequest, session: DbSession) -> TokenResponse:
    """Exchange a refresh token for a fresh pair."""
    try:
        claims = decode_token(payload.refresh_token, TokenType.REFRESH)
    except TokenError as exc:
        raise AuthenticationError(str(exc)) from exc

    user = session.get(User, claims.subject)
    if user is None or not user.is_active:
        raise AuthenticationError("This account is no longer active.")
    return _token_response(user)


@router.get("/me", response_model=UserResponse, summary="Current profile")
def me(user: CurrentUser) -> UserResponse:
    """Return the authenticated learner's profile."""
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse, summary="Update profile")
def update_me(payload: UpdateProfileRequest, user: CurrentUser, session: DbSession) -> UserResponse:
    """Update editable profile fields."""
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.declared_level is not None:
        user.declared_level = payload.declared_level.value
    if payload.goal is not None:
        user.goal = payload.goal
    if payload.active_course_slug is not None:
        user.active_course_slug = payload.active_course_slug
    if payload.preferences is not None:
        user.preferences = {**user.preferences, **payload.preferences}
    session.flush()
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=MessageResponse, summary="Rotate password")
def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, session: DbSession
) -> MessageResponse:
    """Change the authenticated learner's password."""
    AuthService(session).change_password(user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password updated.")
