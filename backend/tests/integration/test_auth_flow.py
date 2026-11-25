"""End-to-end integration tests for Auth (login, rotation, reuse detection, lockout, MFA)."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text

from app.core.auth_store import AuthStore
from app.core.config import get_settings
from app.core.db import Database
from app.core.redis import create_redis, ping_redis
from app.core.security import generate_totp_code, hash_password
from app.main import create_app
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository

pytestmark = pytest.mark.integration


@pytest.fixture
async def auth_env() -> AsyncIterator[tuple[httpx.AsyncClient, uuid.UUID, str, str, str]]:
    try:
        settings = get_settings()
        db = Database(settings)
        redis = create_redis(settings)
    except Exception as exc:
        pytest.skip(f"Settings not loadable from .env: {type(exc).__name__}")

    if not await db.ping() or not await ping_redis(redis):
        await redis.aclose()
        await db.dispose()
        pytest.skip("PostgreSQL or Redis not reachable with .env credentials")

    tenant_id = uuid.uuid4()
    tenant_code = f"auth-{tenant_id.hex[:8]}"
    email = f"user-{tenant_id.hex[:8]}@nexzen.com"
    password = "Correct-Horse-Battery-2026!"

    async with db.transaction(tenant_id) as session:
        await TenantRepository(session, tenant_id).create(
            Tenant(id=tenant_id, tenant_id=tenant_id, code=tenant_code, name="Auth Test Co.")
        )
        await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=email,
                full_name="Test Admin",
                password_hash=hash_password(password),
            )
        )

    app = create_app(settings)
    app.state.settings = settings
    app.state.database = db
    app.state.redis = redis

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        try:
            yield client, tenant_id, tenant_code, email, password
        finally:
            await AuthStore(redis, settings).clear_failed_attempts(tenant_id, email)
            async with db.transaction(tenant_id) as session:
                await session.execute(
                    text("DELETE FROM refresh_tokens WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                )
                await session.execute(
                    text("DELETE FROM users WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                )
                await session.execute(
                    text("DELETE FROM tenants WHERE id = :tid"),
                    {"tid": tenant_id},
                )
            await redis.aclose()
            await db.dispose()


async def test_login_me_refresh_rotation_reuse_detection_and_logout(
    auth_env: tuple[httpx.AsyncClient, uuid.UUID, str, str, str],
) -> None:
    client, _tenant_id, tenant_code, email, password = auth_env

    # 1. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"tenant_code": tenant_code, "email": email, "password": password},
    )
    assert login_res.status_code == 200
    tokens1 = login_res.json()
    assert tokens1["token_type"] == "bearer"

    # 2. /me with access token
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens1['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 3. Refresh token rotation
    ref_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens1["refresh_token"]},
    )
    assert ref_res.status_code == 200
    tokens2 = ref_res.json()
    assert tokens2["refresh_token"] != tokens1["refresh_token"]

    # 4. Reusing old refresh token MUST fail AND revoke the entire token family
    replay_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens1["refresh_token"]},
    )
    assert replay_res.status_code == 401
    victim_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens2["refresh_token"]},
    )
    assert victim_res.status_code == 401

    # 5. Logout revokes the access token in Redis immediately
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens2['access_token']}"},
    )
    assert logout_res.status_code == 204
    revoked_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens2['access_token']}"},
    )
    assert revoked_me.status_code == 401


async def test_login_lockout_after_repeated_failures(
    auth_env: tuple[httpx.AsyncClient, uuid.UUID, str, str, str],
) -> None:
    client, _tenant_id, tenant_code, email, password = auth_env
    max_attempts = get_settings().login_max_attempts

    for _ in range(max_attempts):
        res = await client.post(
            "/api/v1/auth/login",
            json={"tenant_code": tenant_code, "email": email, "password": "wrong-password"},
        )
        assert res.status_code == 401

    # Even with the correct password, the account must now be locked out (429).
    locked = await client.post(
        "/api/v1/auth/login",
        json={"tenant_code": tenant_code, "email": email, "password": password},
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "rate_limited"


async def test_optional_totp_mfa_lifecycle(
    auth_env: tuple[httpx.AsyncClient, uuid.UUID, str, str, str],
) -> None:
    client, _tenant_id, tenant_code, email, password = auth_env

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"tenant_code": tenant_code, "email": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    setup_res = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_res.status_code == 200
    secret = setup_res.json()["secret"]

    enable_res = await client.post(
        "/api/v1/auth/mfa/enable",
        headers=headers,
        json={"otp_code": generate_totp_code(secret)},
    )
    assert enable_res.status_code == 200
    assert enable_res.json()["mfa_enabled"] is True

    # Login without OTP must fail
    no_otp = await client.post(
        "/api/v1/auth/login",
        json={"tenant_code": tenant_code, "email": email, "password": password},
    )
    assert no_otp.status_code == 401

    # Login with valid OTP succeeds
    with_otp = await client.post(
        "/api/v1/auth/login",
        json={
            "tenant_code": tenant_code,
            "email": email,
            "password": password,
            "otp_code": generate_totp_code(secret),
        },
    )
    assert with_otp.status_code == 200

    # Disable MFA
    disable_res = await client.post(
        "/api/v1/auth/mfa/disable",
        headers=headers,
        json={"password": password, "otp_code": generate_totp_code(secret)},
    )
    assert disable_res.status_code == 200
    assert disable_res.json()["mfa_enabled"] is False
