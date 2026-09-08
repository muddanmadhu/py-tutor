"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, AuthorizationError
from app.core.firebase import verify_id_token
from app.core.security import TokenError, TokenType, decode_token
from app.db.session import get_db
from app.models import User
from app.services.auth import AuthService

#: ``auto_error=False`` so a missing header produces our error envelope, not
#: FastAPI's default, keeping every failure shape identical for the client.
_bearer = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[Session, Depends(get_db)]


def _resolve_user(session: Session, token: str) -> User | None:
    """Resolve a bearer token to a user, or ``None`` if it does not identify one.

    Which kind of token this is depends on the deployment. With Firebase
    configured the client presents a Firebase ID token and the matching local
    account is provisioned on first sight; otherwise it presents an access token
    this application issued.
    """
    if get_settings().firebase_auth_enabled:
        identity = verify_id_token(token)
        return AuthService(session).upsert_from_firebase(identity)

    payload = decode_token(token, TokenType.ACCESS)
    return session.get(User, payload.subject)


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Resolve the authenticated user from the bearer token."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authentication required.")
    try:
        user = _resolve_user(session, credentials.credentials)
    except TokenError as exc:
        raise AuthenticationError(str(exc)) from exc

    if user is None or not user.is_active:
        raise AuthenticationError("This account is no longer active.")
    return user


def get_optional_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """Resolve the user if a valid token is present, else ``None``.

    Used by endpoints that serve public content but personalise it when the
    caller is known (course listings, the reference, search).
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        user = _resolve_user(session, credentials.credentials)
    except TokenError:
        return None
    return user if user and user.is_active else None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_author(user: CurrentUser) -> User:
    """Require content-authoring rights."""
    if not user.can_author:
        raise AuthorizationError("This action requires an author or admin account.")
    return user


def require_admin(user: CurrentUser) -> User:
    """Require administrative rights."""
    if not user.is_admin:
        raise AuthorizationError("This action requires an admin account.")
    return user


AuthorUser = Annotated[User, Depends(require_author)]
AdminUser = Annotated[User, Depends(require_admin)]


class Pagination:
    """Standard limit/offset pagination."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=200, description="Page size")] = 50,
        offset: Annotated[int, Query(ge=0, description="Records to skip")] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PaginationParams = Annotated[Pagination, Depends(Pagination)]
