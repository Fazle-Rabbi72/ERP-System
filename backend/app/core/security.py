"""Security primitives: Argon2id password hashing, JWT tokens, and RFC 6238 TOTP MFA."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import quote

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.exceptions import AuthenticationError

JWT_ISSUER = "nexzen-erp"
TOTP_DIGITS = 6
TokenType = Literal["access", "refresh"]

# OWASP-aligned Argon2id parameters (64 MiB memory, 3 iterations, 4 lanes).
_PASSWORD_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# Pre-computed dummy hash used when a login email does not exist so timing matches real checks.
_DUMMY_HASH = _PASSWORD_HASHER.hash("nexzen-dummy-timing-equalizer-password")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _PASSWORD_HASHER.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2id hash in constant time."""
    try:
        return bool(_PASSWORD_HASHER.verify(hashed, plain))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy_password(plain: str) -> None:
    """Run Argon2id verification against a dummy hash to equalize login timing."""
    verify_password(plain, _DUMMY_HASH)


def needs_rehash(hashed: str) -> bool:
    """True when an existing hash uses older Argon2 parameters and should be upgraded."""
    return bool(_PASSWORD_HASHER.check_needs_rehash(hashed))


@dataclass(frozen=True, slots=True)
class TokenPayload:
    sub: uuid.UUID
    tenant_id: uuid.UUID
    jti: uuid.UUID
    token_type: TokenType
    iat: datetime
    exp: datetime
    family_id: uuid.UUID | None = None

    @property
    def remaining_ttl_seconds(self) -> int:
        delta = int((self.exp - datetime.now(UTC)).total_seconds())
        return max(delta, 0)


def _encode_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    kind: TokenType,
    ttl: timedelta,
    family_id: uuid.UUID | None = None,
) -> tuple[str, TokenPayload]:
    now = datetime.now(UTC)
    exp = now + ttl
    jti = uuid.uuid4()
    claims: dict[str, object] = {
        "iss": JWT_ISSUER,
        "sub": str(user_id),
        "tid": str(tenant_id),
        "jti": str(jti),
        "typ": kind,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if family_id is not None:
        claims["fam"] = str(family_id)

    encoded = jwt.encode(
        claims,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    payload = TokenPayload(
        sub=user_id,
        tenant_id=tenant_id,
        jti=jti,
        token_type=kind,
        iat=now,
        exp=exp,
        family_id=family_id,
    )
    return encoded, payload


def create_access_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> tuple[str, TokenPayload]:
    return _encode_token(
        settings,
        user_id=user_id,
        tenant_id=tenant_id,
        kind="access",
        ttl=timedelta(minutes=settings.access_token_ttl_minutes),
    )


def create_refresh_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    family_id: uuid.UUID | None = None,
) -> tuple[str, TokenPayload]:
    return _encode_token(
        settings,
        user_id=user_id,
        tenant_id=tenant_id,
        kind="refresh",
        ttl=timedelta(days=settings.refresh_token_ttl_days),
        family_id=family_id or uuid.uuid4(),
    )


def decode_token(
    settings: Settings,
    token: str,
    *,
    expected_type: TokenType,
) -> TokenPayload:
    """Validate JWT signature, issuer, expiry, and type. Raises AuthenticationError on failure."""
    try:
        raw: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=JWT_ISSUER,
            options={"require": ["iss", "sub", "tid", "jti", "typ", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    if raw.get("typ") != expected_type:
        raise AuthenticationError("Invalid token type.")

    try:
        sub = uuid.UUID(str(raw["sub"]))
        tenant_id = uuid.UUID(str(raw["tid"]))
        jti = uuid.UUID(str(raw["jti"]))
        raw_fam = raw.get("fam")
        family_id = uuid.UUID(str(raw_fam)) if raw_fam is not None else None
        raw_iat = raw["iat"]
        raw_exp = raw["exp"]
        if not isinstance(raw_iat, int | float) or not isinstance(raw_exp, int | float):
            raise ValueError("Invalid numeric timestamp")
        iat = datetime.fromtimestamp(raw_iat, tz=UTC)
        exp = datetime.fromtimestamp(raw_exp, tz=UTC)
    except (ValueError, KeyError, TypeError) as exc:
        raise AuthenticationError("Malformed token claims.") from exc

    if expected_type == "refresh" and family_id is None:
        raise AuthenticationError("Refresh token missing family claim.")

    return TokenPayload(
        sub=sub,
        tenant_id=tenant_id,
        jti=jti,
        token_type=expected_type,
        iat=iat,
        exp=exp,
        family_id=family_id,
    )


# --- Optional TOTP MFA (RFC 6238, SHA-1, 6 digits, 30s period) ---


def generate_totp_secret() -> str:
    """Generate a 160-bit Base32 TOTP secret (compatible with Google/Microsoft Authenticator)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def build_totp_uri(secret: str, *, email: str, issuer: str = "Nexzen ERP") -> str:
    label = quote(f"{issuer}:{email}")
    encoded_issuer = quote(issuer)
    return f"otpauth://totp/{label}?secret={secret}&issuer={encoded_issuer}&digits=6&period=30"


def _totp_at_counter(secret: str, counter: int) -> str:
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code_int % 1_000_000:06d}"


def generate_totp_code(secret: str, *, timestamp: int | None = None) -> str:
    ts = int(time.time()) if timestamp is None else timestamp
    return _totp_at_counter(secret, ts // 30)


def verify_totp(
    secret: str,
    code: str,
    *,
    window: int = 1,
    timestamp: int | None = None,
) -> bool:
    """Verify a 6-digit TOTP code with ±`window` 30-second steps in constant time."""
    cleaned = code.strip()
    if len(cleaned) != TOTP_DIGITS or not cleaned.isdigit():
        return False
    ts = int(time.time()) if timestamp is None else timestamp
    current_counter = ts // 30
    matched = False
    for offset in range(-window, window + 1):
        expected = _totp_at_counter(secret, current_counter + offset)
        if hmac.compare_digest(expected, cleaned):
            matched = True
    return matched
