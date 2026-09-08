"""Authentication and account management."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, ConflictError, ValidationFailure
from app.core.firebase import FirebaseIdentity
from app.core.security import (
    TokenType,
    create_token,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from app.db.base import utcnow
from app.models import User
from app.models.enums import SkillLevel, UserRole


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Issued credentials."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - the OAuth2 scheme name, not a credential


class AuthService:
    """Registration, login and token refresh."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        declared_level: SkillLevel = SkillLevel.BEGINNER,
        goal: str | None = None,
    ) -> User:
        """Create a learner account."""
        normalised = email.strip().lower()
        if self._session.scalar(select(User.id).where(User.email == normalised)):
            raise ConflictError(
                "An account with that email already exists.",
                details={"field": "email"},
            )
        problems = validate_password_strength(password)
        if problems:
            raise ValidationFailure(
                "Password " + ", and ".join(problems) + ".",
                details={"field": "password", "problems": problems},
            )

        user = User(
            email=normalised,
            display_name=display_name.strip() or normalised.split("@")[0],
            password_hash=hash_password(password),
            role=UserRole.LEARNER.value,
            declared_level=declared_level.value,
            goal=goal,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def authenticate(self, email: str, password: str) -> User:
        """Verify credentials and return the user.

        The same error is returned for an unknown email and a wrong password so
        the endpoint cannot be used to enumerate accounts.
        """
        user = self._session.scalar(select(User).where(User.email == email.strip().lower()))
        # A null hash means the account signs in through Firebase and has no
        # password here. Answering with the same generic error keeps that fact
        # from leaking, and there is nothing to verify against regardless.
        if (
            user is None
            or not user.password_hash
            or not verify_password(password, user.password_hash)
        ):
            raise AuthenticationError("Email or password is incorrect.")
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.")

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        user.last_login_at = utcnow()
        self._session.flush()
        return user

    def upsert_from_firebase(self, identity: FirebaseIdentity) -> User:
        """Return the local account for a verified Firebase identity, creating it if new.

        Firebase owns the credential; this table owns the learning record. The
        two are joined on ``firebase_uid``, which is stable even if the learner
        later changes their email address.

        An existing password account with the same email is *adopted* rather
        than duplicated, so someone who registered before Firebase was switched
        on keeps their progress when they sign in with Google.
        """
        user = self._session.scalar(select(User).where(User.firebase_uid == identity.uid))

        if user is None and identity.email:
            user = self._session.scalar(select(User).where(User.email == identity.email))
            if user is not None:
                user.firebase_uid = identity.uid

        if user is None:
            email = identity.email or f"{identity.uid}@firebase.local"
            user = User(
                email=email,
                # The display name is rendered throughout the UI, so it must not
                # be empty even though Firebase treats it as optional.
                display_name=identity.display_name.strip() or email.split("@")[0],
                firebase_uid=identity.uid,
                password_hash=None,
                role=UserRole.LEARNER.value,
                declared_level=SkillLevel.BEGINNER.value,
            )
            self._session.add(user)

        # Flush before reading ``is_active``: on a row this call just created it
        # is a column default, so it stays None in Python until the INSERT runs
        # and would otherwise read as "deactivated".
        self._session.flush()
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.")

        user.last_login_at = utcnow()
        self._session.flush()
        return user

    @staticmethod
    def issue_tokens(user: User) -> TokenPair:
        """Mint an access/refresh pair for ``user``."""
        return TokenPair(
            access_token=create_token(user.id, TokenType.ACCESS),
            refresh_token=create_token(user.id, TokenType.REFRESH),
        )

    def change_password(self, user: User, current: str, new: str) -> None:
        """Rotate a learner's password."""
        if not user.password_hash:
            raise ValidationFailure(
                "This account signs in through Firebase, so it has no password here. "
                "Change it with your identity provider instead."
            )
        if not verify_password(current, user.password_hash):
            raise AuthenticationError("Your current password is incorrect.")
        problems = validate_password_strength(new)
        if problems:
            raise ValidationFailure("New password " + ", and ".join(problems) + ".")
        user.password_hash = hash_password(new)
        self._session.flush()
