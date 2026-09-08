"""Firebase-federated identity.

Verifying a real ID token needs Google's signing keys and a live project, so
these tests cover the half that is ours: how a *verified* identity maps onto a
local account, and that the server refuses to pretend when it is unconfigured.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.firebase import FirebaseIdentity, verify_id_token
from app.core.security import TokenError
from app.models import User
from app.services.auth import AuthService


def identity(**overrides: object) -> FirebaseIdentity:
    """A verified Firebase identity, as the token verifier would return it."""
    fields: dict[str, object] = {
        "uid": "firebase-uid-1",
        "email": "learner@example.com",
        "display_name": "Test Learner",
        "email_verified": True,
    }
    fields.update(overrides)
    return FirebaseIdentity(**fields)  # type: ignore[arg-type]


class TestUpsertFromFirebase:
    """Mapping a Firebase credential onto the local learning record."""

    def test_first_sign_in_provisions_an_account(self, session: Session) -> None:
        user = AuthService(session).upsert_from_firebase(identity(email="new@example.com"))
        assert user.id
        assert user.email == "new@example.com"
        assert user.firebase_uid == "firebase-uid-1"
        # Firebase owns the credential, so there is no password here to leak.
        assert user.password_hash is None

    def test_returning_learner_keeps_the_same_account(self, session: Session) -> None:
        service = AuthService(session)
        first = service.upsert_from_firebase(identity(email="repeat@example.com"))
        session.flush()
        again = service.upsert_from_firebase(identity(email="repeat@example.com"))
        assert first.id == again.id
        assert session.scalar(select(User).where(User.email == "repeat@example.com"))

    def test_an_existing_password_account_is_adopted_not_duplicated(
        self, session: Session, user: User
    ) -> None:
        """Someone who registered before Firebase must not lose their progress."""
        original_id = user.id
        adopted = AuthService(session).upsert_from_firebase(identity(email=user.email))
        assert adopted.id == original_id
        assert adopted.firebase_uid == "firebase-uid-1"

    def test_a_changed_email_still_matches_on_uid(self, session: Session) -> None:
        """The uid is the join key precisely because email is mutable."""
        service = AuthService(session)
        first = service.upsert_from_firebase(identity(email="before@example.com"))
        session.flush()
        after = service.upsert_from_firebase(identity(email="after@example.com"))
        assert after.id == first.id

    def test_a_deactivated_account_is_refused(self, session: Session, user: User) -> None:
        from app.core.errors import AuthenticationError

        user.is_active = False
        session.flush()
        with pytest.raises(AuthenticationError):
            AuthService(session).upsert_from_firebase(identity(email=user.email))

    def test_an_account_without_email_still_gets_one(self, session: Session) -> None:
        """`email` is NOT NULL, and anonymous Firebase sign-in carries no address."""
        created = AuthService(session).upsert_from_firebase(
            identity(uid="anon-uid", email="", display_name="")
        )
        assert created.email
        assert created.display_name


class TestPasswordAuthCoexistence:
    """Local password accounts keep working alongside federated ones."""

    def test_a_firebase_account_cannot_be_signed_into_with_a_password(
        self, session: Session
    ) -> None:
        from app.core.errors import AuthenticationError

        service = AuthService(session)
        service.upsert_from_firebase(identity(email="federated@example.com"))
        session.flush()
        with pytest.raises(AuthenticationError):
            service.authenticate("federated@example.com", "any-password-at-all")

    def test_changing_the_password_of_a_firebase_account_is_refused(self, session: Session) -> None:
        from app.core.errors import ValidationFailure

        service = AuthService(session)
        created = service.upsert_from_firebase(identity(email="federated2@example.com"))
        session.flush()
        with pytest.raises(ValidationFailure):
            service.change_password(created, "old-password", "new-password-1234")


class TestVerificationRequiresConfiguration:
    """An unconfigured server must not accept Firebase tokens."""

    def test_verification_fails_without_a_project_id(self) -> None:
        assert get_settings().firebase_project_id is None
        with pytest.raises(TokenError):
            verify_id_token("any.token.at.all")

    def test_firebase_auth_is_off_by_default(self) -> None:
        assert get_settings().firebase_auth_enabled is False


class TestFirebaseSettings:
    """The configuration switch itself."""

    @pytest.fixture()
    def configured(self) -> Iterator[None]:
        os.environ["PYFORGE_FIREBASE_PROJECT_ID"] = "demo-project"
        get_settings.cache_clear()
        yield
        del os.environ["PYFORGE_FIREBASE_PROJECT_ID"]
        get_settings.cache_clear()

    def test_setting_a_project_id_enables_firebase_auth(self, configured: None) -> None:
        assert get_settings().firebase_auth_enabled is True
        assert get_settings().firebase_project_id == "demo-project"
