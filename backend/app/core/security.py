"""Security primitives: password hashing and JWT issuance/verification.

Password hashing uses :func:`hashlib.scrypt` from the standard library. scrypt
is a memory-hard KDF standardised in RFC 7914 and is a sound choice for
password storage; using the stdlib keeps a security-critical path free of
optional native dependencies that drift between environments.

The stored format is self-describing so parameters can be raised later and old
hashes transparently upgraded on next login:

``scrypt$n=16384,r=8,p=1$<salt-b64>$<hash-b64>``
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

import jwt

from app.core.config import get_settings

# scrypt parameters: ~16 MiB of memory per hash, comfortably above GPU-friendly.
_SCRYPT_N: Final = 2**14
_SCRYPT_R: Final = 8
_SCRYPT_P: Final = 1
_SCRYPT_DKLEN: Final = 32
_SALT_BYTES: Final = 16
_ALGORITHM_TAG: Final = "scrypt"


class TokenType(StrEnum):
    """Kinds of JWT this application issues."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """A token was missing, malformed, expired or of the wrong type."""


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Decoded and validated JWT claims."""

    subject: str
    token_type: TokenType
    jti: str
    issued_at: datetime
    expires_at: datetime


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def hash_password(password: str) -> str:
    """Hash a plaintext password into the self-describing storage format."""
    if not password:
        raise ValueError("password must not be empty")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=64 * 1024 * 1024,
    )
    params = f"n={_SCRYPT_N},r={_SCRYPT_R},p={_SCRYPT_P}"
    return f"{_ALGORITHM_TAG}${params}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of ``password`` against a stored hash.

    Returns ``False`` rather than raising on malformed input so that a corrupt
    row cannot be distinguished from a wrong password by an attacker.
    """
    try:
        algorithm, params, salt_b64, hash_b64 = stored.split("$")
        if algorithm != _ALGORITHM_TAG:
            return False
        parsed = dict(pair.split("=", 1) for pair in params.split(","))
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64decode(salt_b64),
            n=int(parsed["n"]),
            r=int(parsed["r"]),
            p=int(parsed["p"]),
            dklen=_SCRYPT_DKLEN,
            maxmem=64 * 1024 * 1024,
        )
    except (ValueError, KeyError, TypeError):
        return False
    return hmac.compare_digest(candidate, _b64decode(hash_b64))


def needs_rehash(stored: str) -> bool:
    """Whether a stored hash was produced with weaker-than-current parameters."""
    try:
        algorithm, params, _, _ = stored.split("$")
        parsed = dict(pair.split("=", 1) for pair in params.split(","))
    except ValueError:
        return True
    return algorithm != _ALGORITHM_TAG or int(parsed.get("n", 0)) < _SCRYPT_N


def create_token(subject: str, token_type: TokenType) -> str:
    """Issue a signed JWT for ``subject``."""
    settings = get_settings()
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.access_token_ttl_minutes)
        if token_type is TokenType.ACCESS
        else timedelta(days=settings.refresh_token_ttl_days)
    )
    claims: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "iss": settings.app_name,
    }
    return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    """Verify a JWT and return its payload.

    Raises
    ------
    TokenError
        If the signature, expiry, issuer or token type does not check out.
    """
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.app_name,
            options={"require": ["exp", "iat", "sub", "type", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("token is invalid") from exc

    if claims.get("type") != expected_type.value:
        raise TokenError(f"expected a {expected_type.value} token")

    return TokenPayload(
        subject=str(claims["sub"]),
        token_type=TokenType(claims["type"]),
        jti=str(claims["jti"]),
        issued_at=datetime.fromtimestamp(claims["iat"], tz=UTC),
        expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
    )


def validate_password_strength(password: str) -> list[str]:
    """Return a list of human-readable problems, empty when the password is fine."""
    settings = get_settings()
    problems: list[str] = []
    if len(password) < settings.password_min_length:
        problems.append(f"must be at least {settings.password_min_length} characters")
    if password.isdigit() or password.isalpha():
        problems.append("must mix letters with digits or symbols")
    if password.lower() in {"password", "python", "letmein", "qwerty", "pyforge"}:
        problems.append("is too common")
    return problems
