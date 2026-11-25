"""Unit tests for Argon2id password hashing, JWT tokens, and TOTP MFA."""

import uuid

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    build_totp_uri,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_code,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp,
)
from tests.factories import make_settings

pytestmark = pytest.mark.unit


def test_argon2id_hash_and_verify() -> None:
    hashed = hash_password("StrongPass!2026")
    assert hashed.startswith("$argon2id$")
    assert verify_password("StrongPass!2026", hashed) is True
    assert verify_password("WrongPass!2026", hashed) is False
    assert verify_password("anything", "not-a-valid-hash") is False


def test_access_and_refresh_jwt_roundtrip_and_type_separation() -> None:
    settings = make_settings()
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    access_jwt, access_payload = create_access_token(
        settings,
        user_id=user_id,
        tenant_id=tenant_id,
    )
    decoded_access = decode_token(settings, access_jwt, expected_type="access")
    assert decoded_access.sub == user_id
    assert decoded_access.tenant_id == tenant_id
    assert decoded_access.jti == access_payload.jti
    assert decoded_access.family_id is None

    with pytest.raises(AuthenticationError):
        decode_token(settings, access_jwt, expected_type="refresh")

    refresh_jwt, refresh_payload = create_refresh_token(
        settings,
        user_id=user_id,
        tenant_id=tenant_id,
    )
    decoded_refresh = decode_token(settings, refresh_jwt, expected_type="refresh")
    assert decoded_refresh.family_id == refresh_payload.family_id
    assert decoded_refresh.family_id is not None

    with pytest.raises(AuthenticationError):
        decode_token(settings, refresh_jwt, expected_type="access")


def test_jwt_rejected_with_different_secret() -> None:
    s1 = make_settings(jwt_secret_key="a" * 48)
    s2 = make_settings(jwt_secret_key="b" * 48)
    token, _ = create_access_token(s1, user_id=uuid.uuid4(), tenant_id=uuid.uuid4())

    with pytest.raises(AuthenticationError):
        decode_token(s2, token, expected_type="access")


def test_totp_generation_verification_and_window() -> None:
    secret = generate_totp_secret()
    uri = build_totp_uri(secret, email="admin@nexzen.bd")
    assert uri.startswith("otpauth://totp/")
    assert secret in uri

    ts = 1_700_000_000
    code = generate_totp_code(secret, timestamp=ts)
    assert len(code) == 6
    assert code.isdigit()
    assert verify_totp(secret, code, timestamp=ts) is True
    # Within ±1 step (30s) still valid; 90s away must fail.
    assert verify_totp(secret, code, timestamp=ts + 30) is True
    assert verify_totp(secret, code, timestamp=ts + 90) is False
    assert verify_totp(secret, "abcdef", timestamp=ts) is False
