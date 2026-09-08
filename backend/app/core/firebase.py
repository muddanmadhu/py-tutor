"""Firebase ID token verification.

Firebase Authentication runs entirely in the browser: the client signs in, gets
an ID token, and sends it as a bearer token. This module is the server half —
it checks that a presented token really was issued by Firebase for *our*
project and has not expired.

Verification is done against Google's published JWKS rather than through the
``firebase-admin`` SDK. Both are equally sound, but JWKS needs only the public
project id, where the SDK needs a service-account private key — one more secret
to mount, rotate and leak. The project id is not a credential.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import TokenError

logger = get_logger(__name__)

#: Google's rotating public keys for Firebase-issued ID tokens.
_JWKS_URL = (
    "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
)

#: Firebase always signs ID tokens with RS256.
_ALGORITHMS = ["RS256"]


@dataclass(frozen=True, slots=True)
class FirebaseIdentity:
    """The verified claims we actually use."""

    uid: str
    email: str
    display_name: str
    email_verified: bool


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    """Return a process-wide JWKS client.

    ``PyJWKClient`` caches the key set and refetches when it sees an unknown
    ``kid``, so Google's key rotation is handled without us tracking it.
    """
    return PyJWKClient(_JWKS_URL, cache_keys=True)


def verify_id_token(token: str) -> FirebaseIdentity:
    """Verify a Firebase ID token and return its identity.

    Raises
    ------
    TokenError
        If the token is malformed, expired, signed by the wrong key, or issued
        for a different Firebase project.
    """
    project_id = get_settings().firebase_project_id
    if not project_id:
        raise TokenError("Firebase authentication is not configured on this server.")

    try:
        signing_key = _jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=_ALGORITHMS,
            # Firebase sets the audience to the project id and the issuer to
            # securetoken.google.com/<project id>. Checking both is what stops a
            # valid token from *another* Firebase project authenticating here.
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        # The reason is useful in logs but must not reach the client, which
        # would learn whether a token was merely expired or entirely forged.
        logger.info("firebase token rejected: %s", exc)
        raise TokenError("Your session is no longer valid. Please sign in again.") from exc
    except Exception as exc:  # JWKS fetch failure — a server problem, not the caller's
        logger.warning("firebase JWKS lookup failed: %s", exc)
        raise TokenError("Could not verify your session. Please try again.") from exc

    uid = str(claims.get("sub") or "")
    if not uid:
        raise TokenError("Your session is no longer valid. Please sign in again.")

    email = str(claims.get("email") or "").strip().lower()
    return FirebaseIdentity(
        uid=uid,
        email=email,
        # Firebase omits name for email/password accounts that never set one.
        display_name=str(claims.get("name") or "").strip()
        or (email.split("@")[0] if email else uid),
        email_verified=bool(claims.get("email_verified")),
    )
